"""Summarize arXiv papers in Korean using Gemini."""
import re

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_API_KEY)

_SYSTEM_PROMPT = (
    "너는 논문 요약 전문가다. 짧고 직접적으로만 답한다.\n"
    "규칙:\n"
    "- 한국어로만 답한다. 단, 전문 용어(technical terms)는 영어 원문 그대로 쓰고 번역하지 않는다.\n"
    "- 초록에 명시된 내용만 쓴다. 없는 항목은 '명시 안 됨'이라고 쓴다. 절대 지어내지 않는다.\n"
    "- 추측이 들어가면 반드시 '(추측)'을 붙인다.\n"
    "- 마크다운 표(|---|)나 #헤더, **굵게**를 절대 쓰지 않는다. 카카오톡은 이를 렌더링하지 못한다.\n"
    "- 각 항목은 'ㆍ항목명: 내용' 형태의 한 줄로만 쓴다.\n"
    "- LaTeX 수식 기호($, \\rightleftharpoons 등)를 쓰지 않고 일반 텍스트로 푼다.\n"
    "- YouTube 링크를 제공하지 않는다.\n"
    "- 거짓을 말하지 않는다. 출력 전에 hallucination 여부를 스스로 점검한다."
)

_model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    system_instruction=_SYSTEM_PROMPT,
)

# 카카오톡 메시지 1통 글자수 상한 (전송 API에 맞춰 조정)
KAKAO_MSG_LIMIT = 950 # 수정


# 분야별 항목 정의. 카톡 가독성 위해 핵심 5개로 압축.
_TABLE_SCHEMAS: dict[str, list[str]] = {
    "reinforcement learning": [
        "문제 정의", "State/Action", "Reward", "학습 알고리즘", "결과",
    ],
    "navigation": [
        "문제 정의", "State/Action", "Reward", "학습 알고리즘", "결과",
    ],
    "vla": [
        "문제 정의", "입력 모달리티", "Action / 아키텍처", "학습 방식", "결과",
    ],
    "world model": [
        "문제 정의", "예측 대상", "모델 아키텍처", "활용 방식", "결과",
    ],
    "slam": [
        "문제 정의", "센서 입력", "맵 표현", "최적화 방식", "결과",
    ],
    "robotics": [  # 범용 fallback
        "문제 정의", "입력/출력", "핵심 방법", "플랫폼", "결과",
    ],
}

# 토픽 식별용 키워드 → 스키마 키 매핑 (긴 것/구체적인 것부터 매칭)
_TOPIC_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("vision language action", "vision-language-action", "vla"), "vla"),
    (("world model",), "world model"),
    (("slam", "simultaneous localization"), "slam"),
    (("navigation", "local planner", "obstacle avoidance"), "navigation"),
    (("reinforcement learning", "policy", "reward"), "reinforcement learning"),
]


def _pick_schema(paper: dict) -> tuple[str, list[str]]:
    """제목+초록+카테고리에서 토픽을 추정해 항목 스키마를 고른다. 못 찾으면 robotics."""
    text = " ".join([
        paper.get("title", ""),
        paper.get("abstract", ""),
        " ".join(paper.get("categories", [])),
    ]).lower()

    for hints, key in _TOPIC_HINTS:
        if any(h in text for h in hints):
            return key, _TABLE_SCHEMAS[key]
    return "robotics", _TABLE_SCHEMAS["robotics"]


def summarize_paper(paper: dict) -> str:
    """논문 1편을 토픽에 맞는 텍스트 형식으로 한국어 요약한다 (카카오톡용)."""
    topic, fields = _pick_schema(paper)
    field_lines = "\n".join(f"ㆍ{f}: " for f in fields)

    prompt = (
        f"제목: {paper['title']}\n"
        f"저자: {', '.join(paper['authors'])}\n"
        f"초록: {paper['abstract']}\n\n"
        f"위 논문을 아래 항목 형식으로 채워라. (추정 토픽: {topic})\n"
        "지침:\n"
        "- 마크다운 표, 헤더, 굵게, LaTeX 기호 금지. 카카오톡 평문으로만.\n"
        "- 각 항목은 'ㆍ항목명: 내용' 한 줄. 내용은 1문장(최대 2문장), 한 줄이 너무 길지 않게.\n"
        "- '문제 정의'만 예외로, abstract 복붙 말고 이 연구가 본질적으로 뭘 설계/해결하려는 건지, "
        "무엇을 대체하고 무엇은 대체 안 하는지 insight를 담아라. 그래도 2문장 이내.\n"
        "- 초록에 없으면 '명시 안 됨', 추측이면 '(추측)'.\n"
        "- 전문 용어는 영어 원문 그대로.\n\n"
        f"{field_lines}\n\n"
        "마지막 줄에 'ㆍ한줄평: '으로 핵심 코멘트 1줄."
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

    indices = [int(x) for x in re.findall(r"\d+", raw) if int(x) < len(candidates)]
    seen: set[int] = set()
    unique = [i for i in indices if not (i in seen or seen.add(i))]  # type: ignore[func-returns-value]
    selected = [candidates[i] for i in unique[:top_n]]

    if len(selected) < top_n:
        already = set(unique[:top_n])
        for j, p in enumerate(candidates):
            if j not in already:
                selected.append(p)
            if len(selected) == top_n:
                break

    return selected


def _split_for_kakao(text: str, limit: int = KAKAO_MSG_LIMIT) -> list[str]:
    """카카오톡 길이 제한에 맞춰 줄 단위로 분할. 한 줄이 limit보다 길면 강제로 자른다."""
    chunks: list[str] = []
    buf = ""
    for line in text.split("\n"):
        # 한 줄 자체가 limit 초과 시 조각냄
        while len(line) > limit:
            if buf:
                chunks.append(buf.rstrip("\n"))
                buf = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(buf) + len(line) + 1 > limit:
            chunks.append(buf.rstrip("\n"))
            buf = ""
        buf += line + "\n"
    if buf.strip():
        chunks.append(buf.rstrip("\n"))
    return chunks


def build_paper_messages(paper: dict, index: int, total: int, summary: str) -> list[str]:
    """
    한 논문을 카카오톡 메시지 리스트로 포맷. summary를 자르지 않고,
    길이 제한 초과 시 여러 통으로 분할한다. (이전 summary[:350] 강제절단 제거)
    """
    authors = ", ".join(paper["authors"])
    if paper.get("more_authors", 0):
        authors += f" 외 {paper['more_authors']}명"

    full = (
        f"[{index}/{total}] {paper['title']}\n"
        f"✍  {authors}\n"
        f"📅 {paper['published']}\n\n"
        f"{summary}\n\n"
        f"🔗 {paper['url']}"
    )
    return _split_for_kakao(full)