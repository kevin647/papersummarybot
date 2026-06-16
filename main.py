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


def _load_and_resend(date: str):
    """Parse an existing digest markdown and re-send it via KakaoTalk."""
    import re as _re
    from kakao_notifier import send_papers

    md_path = Path(PAPER_SAVE_DIR) / date / f"{date}.md"
    text = md_path.read_text(encoding="utf-8")

    # Extract optional form URL
    form_url = ""
    m = _re.search(r"\*\*별점 입력.*?\*\*:?\s*(https?://\S+)", text)
    if m:
        form_url = m.group(1).strip()

    # Split into per-paper blocks  (## [1/N] Title …)
    blocks = _re.split(r"\n(?=## \[\d+/\d+\])", text)

    results: list[tuple[dict, str]] = []
    for block in blocks:
        if not block.startswith("## ["):
            continue
        title_m   = _re.match(r"## \[\d+/\d+\]\s+(.+)", block)
        author_m  = _re.search(r"\|\s*\*\*저자\*\*\s*\|\s*(.+?)\s*\|", block)
        date_m    = _re.search(r"\|\s*\*\*날짜\*\*\s*\|\s*(.+?)\s*\|", block)
        url_m     = _re.search(r"\|\s*\*\*arXiv\*\*\s*\|\s*(https?://\S+)\s*\|", block)
        summary_m = _re.search(r"### 요약\s*\n\n(.+?)\n\n### 별점", block, _re.DOTALL)

        if not (title_m and summary_m):
            continue

        raw_authors = author_m.group(1).strip() if author_m else ""
        # 외 N명 suffix → more_authors
        extra_m = _re.search(r"\s+외\s+(\d+)명$", raw_authors)
        more_authors = int(extra_m.group(1)) if extra_m else 0
        authors_clean = _re.sub(r"\s+외\s+\d+명$", "", raw_authors)

        paper = {
            "title":       title_m.group(1).strip(),
            "authors":     [a.strip() for a in authors_clean.split(",") if a.strip()],
            "more_authors": more_authors,
            "published":   date_m.group(1).strip() if date_m else date,
            "url":         url_m.group(1).strip() if url_m else "",
        }
        results.append((paper, summary_m.group(1).strip()))

    if not results:
        log.warning("저장된 논문을 파싱할 수 없습니다.")
        return

    # ── Re-summarize option ───────────────────────────────────────────────────
    ans_resummary = input("요약을 새로 생성할까요? (y/n): ").strip().lower()
    if ans_resummary == "y":
        import re as _re2
        import arxiv as _arxiv
        from summarizer import summarize_paper

        new_results: list[tuple[dict, str]] = []
        total = len(results)
        for i, (paper, old_summary) in enumerate(results, 1):
            # Extract arXiv ID from URL  (e.g. https://arxiv.org/abs/2506.12345 → 2506.12345)
            arxiv_id_m = _re2.search(r"arxiv\.org/abs/(.+?)(?:v\d+)?$", paper["url"])
            if not arxiv_id_m:
                log.warning(f"  [{i}/{total}] arXiv ID 추출 실패, 기존 요약 유지: {paper['url']}")
                new_results.append((paper, old_summary))
                continue

            arxiv_id = arxiv_id_m.group(1).strip()
            try:
                search = _arxiv.Search(id_list=[arxiv_id])
                result = next(_arxiv.Client().results(search))
                paper["abstract"] = result.summary.replace("\n", " ").strip()
                log.info(f"  [{i}/{total}] 재요약 중: {paper['title'][:60]}…")
                new_summary = summarize_paper(paper)
                new_results.append((paper, new_summary))
            except Exception as e:
                log.warning(f"  [{i}/{total}] 재요약 실패, 기존 요약 유지: {e}")
                new_results.append((paper, old_summary))

        results = new_results

        # Overwrite the MD with updated summaries
        from paper_saver import save_daily
        save_daily(results, form_url=form_url, base_dir=PAPER_SAVE_DIR)
        log.info("MD 파일 업데이트 완료.")

    log.info(f"{len(results)}편 재전송 중…")
    send_papers(results, form_url=form_url)
    log.info("재전송 완료.")


def main():
    log.info(f"Paper alert started.  Scheduled daily at {DAILY_RUN_TIME} (local time).")

    yesterday = _yesterday_kst()
    if _digest_exists(yesterday):
        log.info(f"어제({yesterday}) digest 이미 존재.")
        ans = input("카카오로 다시 보낼까요? (y/n): ").strip().lower()
        if ans == "y":
            _load_and_resend(yesterday)
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
