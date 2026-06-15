"""Fetch recent arXiv papers that match the configured topics."""
from datetime import datetime, timedelta, timezone

import arxiv

from config import ARXIV_CATEGORIES, CANDIDATE_POOL_SIZE, SEARCH_KEYWORDS

# KST = UTC+9
_KST = timezone(timedelta(hours=9))


def _kst_yesterday_window() -> tuple[datetime, datetime]:
    """
    Return the UTC start and end of 'yesterday' in KST.

    Example (script runs 2026-06-16 08:00 KST):
      yesterday KST  = 2026-06-15 00:00 ~ 2026-06-16 00:00 KST
      in UTC         = 2026-06-14 15:00 ~ 2026-06-15 15:00 UTC
    """
    now_kst = datetime.now(_KST)
    today_kst_midnight = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_kst_midnight = today_kst_midnight - timedelta(days=1)
    return (
        yesterday_kst_midnight.astimezone(timezone.utc),
        today_kst_midnight.astimezone(timezone.utc),
    )


def fetch_recent_papers() -> list[dict]:
    """
    Return papers published on 'yesterday (KST)' that contain at least one
    search keyword in the target arXiv categories.
    Returns up to CANDIDATE_POOL_SIZE papers for downstream Gemini ranking.
    """
    window_start, window_end = _kst_yesterday_window()

    keyword_query = " OR ".join(f'"{kw}"' for kw in SEARCH_KEYWORDS)
    cat_query     = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    query         = f"({keyword_query}) AND ({cat_query})"

    client = arxiv.Client(page_size=100, delay_seconds=3)
    search = arxiv.Search(
        query=query,
        max_results=200,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    papers: list[dict] = []
    for result in client.results(search):
        pub = result.published
        # arXiv returns newest first; once we go before window_start, stop
        if pub < window_start:
            break
        if window_start <= pub < window_end:
            papers.append(
                {
                    "id":           result.entry_id,
                    "title":        result.title.strip(),
                    "authors":      [str(a) for a in result.authors[:5]],
                    "more_authors": max(0, len(result.authors) - 5),
                    "abstract":     result.summary.replace("\n", " ").strip(),
                    "url":          result.entry_id,
                    "pdf_url":      result.pdf_url,
                    "published":    result.published.astimezone(_KST).strftime("%Y-%m-%d"),
                    "categories":   result.categories,
                }
            )
            if len(papers) >= CANDIDATE_POOL_SIZE:
                break

    return papers
