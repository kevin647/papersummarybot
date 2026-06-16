import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_ACCESS_TOKEN = os.getenv("KAKAO_ACCESS_TOKEN", "")
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN", "")

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-3.1-pro-preview"

# ── Paper search ──────────────────────────────────────────────────────────────
SEARCH_KEYWORDS = [
    # navigation / mapping
    "navigation",
    "SLAM",
    "simultaneous localization and mapping",
    # learning paradigms
    "reinforcement learning",
    "world model",
    "world models",
    # VLA / multimodal policy
    "VLA",
    "vision language action",
    "vision-language-action",
    # 'robotics' 단독은 cat 필터와 중복 → 구체화하거나 제거
    "manipulation",
    "humanoid",
]

# How many candidates to pull from arXiv before Gemini selects the best N
CANDIDATE_POOL_SIZE = 200

ARXIV_CATEGORIES = ["cs.RO", "cs.LG", "cs.AI", "cs.CV", "cs.CL"]

# Max number of papers to include in a single daily digest
MAX_PAPERS_PER_DAY = 5

# ── Paper save directory ─────────────────────────────────────────────────────
# 구글 드라이브 경로로 변경하면 자동 동기화됨
# 예: C:\Users\user\Google Drive\My Drive\papers
PAPER_SAVE_DIR = os.getenv("PAPER_SAVE_DIR", "paper")

# ── Schedule ──────────────────────────────────────────────────────────────────
# 24-hour local time at which the daily digest runs
DAILY_RUN_TIME = "08:00"
