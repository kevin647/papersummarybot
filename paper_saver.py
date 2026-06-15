"""Download PDFs and save a consolidated daily markdown summary."""
import re
import time
from pathlib import Path

import requests


def _safe_name(text: str) -> str:
    safe = re.sub(r'[\\/*?:"<>|]', "", text)
    return re.sub(r"\s+", " ", safe).strip()[:80]


def _download_pdf(paper: dict, folder: Path):
    pdf_url = paper.get("pdf_url", "")
    if not pdf_url:
        return
    title    = _safe_name(paper["title"])
    pdf_path = folder / f"{title}.pdf"
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        return
    try:
        time.sleep(1)
        resp = requests.get(pdf_url, timeout=60, stream=True)
        resp.raise_for_status()
        with open(pdf_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        print(f"[WARN] PDF download failed for '{title}': {e}")


def save_daily(
    papers_summaries: list[tuple[dict, str]],
    form_url: str = "",
    base_dir: str = "paper",
) -> Path:
    """
    Save all papers to paper/{date}.md and PDFs to paper/{date}/.
    Returns the path to the MD file.
    """
    if not papers_summaries:
        return Path(base_dir)

    date       = papers_summaries[0][0]["published"]
    pdf_folder = Path(base_dir) / date
    pdf_folder.mkdir(parents=True, exist_ok=True)
    md_path    = pdf_folder / f"{date}.md"

    lines = [f"# 논문 요약 — {date}\n\n"]
    if form_url:
        lines.append(f"> 📝 **별점 입력 (폰에서 열기):** {form_url}\n\n")
    lines.append("---\n\n")

    total = len(papers_summaries)
    for i, (paper, summary) in enumerate(papers_summaries, 1):
        authors = ", ".join(paper["authors"])
        if paper.get("more_authors", 0):
            authors += f" 외 {paper['more_authors']}명"
        cats = ", ".join(paper.get("categories", []))

        lines.append(f"## [{i}/{total}] {paper['title']}\n\n")
        lines.append(f"| | |\n|--|--|\n")
        lines.append(f"| **저자** | {authors} |\n")
        lines.append(f"| **카테고리** | {cats} |\n")
        lines.append(f"| **날짜** | {paper['published']} |\n")
        lines.append(f"| **arXiv** | {paper['url']} |\n\n")
        lines.append(f"### 요약\n\n{summary}\n\n")
        lines.append(f"### 별점\n\n<!-- rating_{i} -->⭐ _/5<!-- /rating_{i} -->\n\n---\n\n")

    md_path.write_text("".join(lines), encoding="utf-8")

    for paper, _ in papers_summaries:
        _download_pdf(paper, pdf_folder)

    return md_path


def update_ratings(date: str, ratings: dict[int, int], base_dir: str = "paper"):
    """
    Update ratings in paper/{date}.md.
    ratings = {1-based_paper_index: score (1-5)}
    """
    md_path = Path(base_dir) / date / f"{date}.md"
    if not md_path.exists():
        return
    content = md_path.read_text(encoding="utf-8")
    for idx, score in ratings.items():
        stars   = "⭐" * score
        content = re.sub(
            rf"<!-- rating_{idx} -->.*?<!-- /rating_{idx} -->",
            f"<!-- rating_{idx} -->{stars} {score}/5<!-- /rating_{idx} -->",
            content,
        )
    md_path.write_text(content, encoding="utf-8")
