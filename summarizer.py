"""Summarize arXiv papers in Korean using Gemini."""
import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_API_KEY)

_SYSTEM_PROMPT = (
    "너는 논문 요약 전문가야. "
    "무조건 짧고 직접적으로 말해. "
    "Never provide YouTube links."
    "DO NOT FACTUALLY LIE TO ME."
    "DO NOT FORGET THE DETAILS."
    "Always think step by step. Do not be disrespectful. Double check if you are hallucinating or not."
    "한국어로만 답해."
)

_model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    system_instruction=_SYSTEM_PROMPT,
)


def summarize_paper(paper: dict) -> str:
    """Return a structured Korean summary for one paper."""
    prompt = (
        f"제목: {paper['title']}\n"
        f"저자: {', '.join(paper['authors'])}\n"
        f"초록: {paper['abstract']}\n\n"
        "위 논문을 아래 형식으로 요약해. 각 항목은 2~3문장 이내로만.\n\n"
        "(1) 한줄요약: 이 논문이 뭔지 한 문장으로.\n"
        "(2) 기여점: 이 논문이 뭘 새로 했는지.\n"
        "(3) 구현방법: 어떻게 만들었는지 짧게."
    )
    response = _model.generate_content(prompt)
    return response.text.strip()


def select_top_papers(candidates: list[dict], top_n: int = 5) -> list[dict]:
    """
    Ask Gemini to pick the `top_n` most representative papers from `candidates`.
    Selection criteria: novelty, real-world impact, author reputation, and
    relevance to robotics / RL / world model / VLA / navigation / SLAM.
    Returns the selected papers in ranked order.
    """
    if len(candidates) <= top_n:
        return candidates

    # Build a numbered list of titles + authors + short abstract snippet
    lines = []
    for i, p in enumerate(candidates):
        authors = ", ".join(p["authors"])
        snippet = p["abstract"][:300]
        lines.append(f"[{i}] {p['title']}\n    Authors: {authors}\n    Abstract: {snippet}")

    catalog = "\n\n".join(lines)

    prompt = (
        f"아래는 오늘 arXiv에 올라온 논문 후보 {len(candidates)}편이야.\n"
        "robotics, reinforcement learning, world model, VLA, navigation, SLAM 분야에서 "
        f"가장 임팩트 있고 대표할만한 논문 {top_n}편을 골라줘.\n"
        "선정 기준: 참신성, 실용성, 저자 명성, 분야 기여도.\n"
        f"반드시 인덱스 번호만 쉼표로 구분해서 딱 {top_n}개만 답해. 예시: 3,7,12,21,34\n"
        "다른 말은 하지마. 숫자만.\n\n"
        + catalog
    )

    response = _model.generate_content(prompt)
    raw = response.text.strip()

    # Parse the comma-separated indices robustly
    import re
    indices = [int(x) for x in re.findall(r"\d+", raw) if int(x) < len(candidates)]
    # Deduplicate while preserving order
    seen: set[int] = set()
    unique = [i for i in indices if not (i in seen or seen.add(i))]  # type: ignore[func-returns-value]
    selected = [candidates[i] for i in unique[:top_n]]

    # Fallback: if Gemini returned too few, pad with remaining candidates
    if len(selected) < top_n:
        already = set(unique[:top_n])
        for j, p in enumerate(candidates):
            if j not in already:
                selected.append(p)
            if len(selected) == top_n:
                break

    return selected


def build_paper_message(paper: dict, index: int, total: int, summary: str) -> str:
    """Format one paper for a KakaoTalk feed message."""
    authors = ", ".join(paper["authors"])
    if paper.get("more_authors", 0):
        authors += f" 외 {paper['more_authors']}명"

    return (
        f"[{index}/{total}] {paper['title']}\n"
        f"✍  {authors}\n"
        f"📅 {paper['published']}\n\n"
        f"{summary[:350]}\n\n"
        f"🔗 {paper['url']}"
    )
