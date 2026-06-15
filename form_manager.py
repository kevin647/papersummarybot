"""Create Google Forms for paper rating and read responses."""
import json
import pickle
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

_SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
]

_TOKEN_PATH = Path(__file__).parent / "google_token.pickle"
_CREDS_PATH = Path(__file__).parent / "google_credentials.json"
_STATE_PATH = Path(__file__).parent / "forms_state.json"


def _get_creds():
    creds = None
    if _TOKEN_PATH.exists():
        creds = pickle.loads(_TOKEN_PATH.read_bytes())
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _CREDS_PATH.exists():
                raise FileNotFoundError(
                    "google_credentials.json 없음.\n"
                    "setup_google.py 를 먼저 실행하고 안내를 따르세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS_PATH), _SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN_PATH.write_bytes(pickle.dumps(creds))
    return creds


def _load_state() -> dict:
    if _STATE_PATH.exists():
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_state(state: dict):
    _STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def create_rating_form(papers: list[dict], date: str) -> str:
    """
    Create a Google Form for rating papers.
    Returns the form URL (viewform link).
    """
    creds   = _get_creds()
    service = build("forms", "v1", credentials=creds)

    result  = service.forms().create(body={"info": {"title": f"논문 별점 — {date}"}}).execute()
    form_id = result["formId"]

    items = []
    for i, paper in enumerate(papers):
        authors = ", ".join(paper["authors"])
        if paper.get("more_authors", 0):
            authors += f" 외 {paper['more_authors']}명"
        cats = ", ".join(paper.get("categories", []))

        items.append({
            "createItem": {
                "item": {
                    "title": f"[{i + 1}] {paper['title']}",
                    "description": (
                        f"저자: {authors}\n"
                        f"카테고리: {cats}\n"
                        f"URL: {paper['url']}"
                    ),
                    "questionItem": {
                        "question": {
                            "required": False,
                            "scaleQuestion": {
                                "low": 1,
                                "high": 5,
                                "lowLabel": "별로",
                                "highLabel": "최고",
                            },
                        }
                    },
                },
                "location": {"index": i},
            }
        })

    service.forms().batchUpdate(
        formId=form_id, body={"requests": items}
    ).execute()

    form_url = f"https://docs.google.com/forms/d/{form_id}/viewform"

    state = _load_state()
    state[date] = {"form_id": form_id, "num_papers": len(papers)}
    _save_state(state)

    return form_url


def get_ratings(date: str) -> dict[int, int]:
    """
    Fetch the latest form response for the given date.
    Returns {1-based_paper_index: score (1-5)}.
    Returns empty dict if no responses yet.
    """
    state = _load_state()
    if date not in state:
        return {}

    form_id = state[date]["form_id"]
    creds   = _get_creds()
    service = build("forms", "v1", credentials=creds)

    # Map question_id → 1-based index using title "[N] ..."
    form_data = service.forms().get(formId=form_id).execute()
    q_to_idx: dict[str, int] = {}
    for item in form_data.get("items", []):
        if "questionItem" in item:
            q_id = item["questionItem"]["question"]["questionId"]
            m    = re.match(r"\[(\d+)\]", item.get("title", ""))
            if m:
                q_to_idx[q_id] = int(m.group(1))

    resp_data = service.forms().responses().list(formId=form_id).execute()
    if not resp_data.get("responses"):
        return {}

    latest  = resp_data["responses"][-1]
    ratings: dict[int, int] = {}
    for q_id, answer in latest.get("answers", {}).items():
        if q_id in q_to_idx:
            val = answer.get("textAnswers", {}).get("answers", [{}])[0].get("value", "")
            try:
                ratings[q_to_idx[q_id]] = int(val)
            except (ValueError, IndexError):
                pass

    return ratings
