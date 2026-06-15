"""
arXiv Paper Alert — daily digest via KakaoTalk.

Usage:
    python main.py          # checks if today's digest is missing, runs if needed, then schedules
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import schedule

from config import DAILY_RUN_TIME, PAPER_SAVE_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(Path(__file__).parent / "paper_alert.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))


def _yesterday_kst() -> str:
    return (datetime.now(_KST) - timedelta(days=1)).strftime("%Y-%m-%d")


def _digest_exists(date: str) -> bool:
    """Return True if paper/{date}/{date}.md already exists."""
    return (Path(PAPER_SAVE_DIR) / date / f"{date}.md").exists()


def run_digest():
    """Fetch today's papers, summarize with Gemini, and send to KakaoTalk."""
    log.info("── Daily digest started ──")
    try:
        from arxiv_client   import fetch_recent_papers
        from summarizer     import summarize_paper, select_top_papers
        from kakao_notifier import send_papers, send_text
        from paper_saver    import save_daily
        from config         import PAPER_SAVE_DIR, MAX_PAPERS_PER_DAY

        candidates = fetch_recent_papers()
        if not candidates:
            log.info("No new papers found for yesterday (KST).")
            send_text("📭 어제(KST 기준) 관련 새 논문이 없습니다.")
            return

        log.info(f"Candidate pool: {len(candidates)} paper(s). Asking Gemini to select top {MAX_PAPERS_PER_DAY}…")
        papers = select_top_papers(candidates, top_n=MAX_PAPERS_PER_DAY)
        log.info(f"Selected {len(papers)} paper(s). Generating summaries…")

        results: list[tuple[dict, str]] = []
        total = len(papers)
        for i, paper in enumerate(papers, 1):
            log.info(f"  [{i}/{total}] {paper['title'][:70]}…")
            summary = summarize_paper(paper)
            results.append((paper, summary))

        # Google Form 생성 (google_credentials.json 없으면 건너뜀)
        form_url = ""
        try:
            from form_manager import create_rating_form
            date     = papers[0]["published"]
            form_url = create_rating_form(papers, date)
            log.info(f"Rating form: {form_url}")
        except FileNotFoundError:
            log.info("google_credentials.json 없음 — 폼 생성 건너뜀. setup_google.py 실행 시 활성화됨.")
        except Exception as e:
            log.warning(f"Form creation failed: {e}")

        md_path = save_daily(results, form_url=form_url, base_dir=PAPER_SAVE_DIR)
        log.info(f"저장됨: {md_path}")

        log.info("Sending to KakaoTalk…")
        send_papers(results, form_url=form_url)
        log.info("── Digest sent successfully ──")

    except Exception:
        log.exception("Digest failed — will retry at next scheduled run.")


def check_ratings():
    """Check for new form responses and update the MD files."""
    try:
        from form_manager import get_ratings, _load_state
        from paper_saver  import update_ratings
        from config       import PAPER_SAVE_DIR

        state = _load_state()
        for date in state:
            ratings = get_ratings(date)
            if ratings:
                update_ratings(date, ratings, base_dir=PAPER_SAVE_DIR)
                log.info(f"별점 업데이트 ({date}): {ratings}")
    except FileNotFoundError:
        pass  # Google 미설정
    except Exception as e:
        log.warning(f"Rating check failed: {e}")


def main():
    log.info(f"Paper alert started.  Scheduled daily at {DAILY_RUN_TIME} (local time).")

    yesterday = _yesterday_kst()
    if _digest_exists(yesterday):
        log.info(f"어제({yesterday}) digest 이미 존재 — 스케줄만 등록합니다.")
    else:
        log.info(f"어제({yesterday}) digest 없음 — 지금 즉시 실행합니다.")
        run_digest()

    schedule.every().day.at(DAILY_RUN_TIME).do(run_digest)
    schedule.every(1).hours.do(check_ratings)
    log.info("Waiting for next scheduled run.  Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
