"""Send messages to yourself via KakaoTalk 나에게 보내기 API."""
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

_ENV_PATH = Path(__file__).parent / ".env"


def _cfg() -> dict:
    """Re-read .env so freshly-refreshed tokens are always used."""
    load_dotenv(_ENV_PATH, override=True)
    return {
        "access_token":  os.getenv("KAKAO_ACCESS_TOKEN", ""),
        "refresh_token": os.getenv("KAKAO_REFRESH_TOKEN", ""),
        "rest_api_key":  os.getenv("KAKAO_REST_API_KEY",  ""),
        "client_secret": os.getenv("KAKAO_CLIENT_SECRET", ""),
    }


def _refresh_access_token() -> str:
    """Use the refresh token to obtain a new access token and persist it."""
    cfg  = _cfg()
    payload = {
        "grant_type":    "refresh_token",
        "client_id":     cfg["rest_api_key"],
        "refresh_token": cfg["refresh_token"],
    }
    if cfg["client_secret"]:
        payload["client_secret"] = cfg["client_secret"]
    resp = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data=payload,
        timeout=15,
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"Kakao token refresh failed: {data}")

    set_key(str(_ENV_PATH), "KAKAO_ACCESS_TOKEN", data["access_token"])
    if "refresh_token" in data:                              # returned when near expiry
        set_key(str(_ENV_PATH), "KAKAO_REFRESH_TOKEN", data["refresh_token"])
    os.environ["KAKAO_ACCESS_TOKEN"] = data["access_token"]
    print("Kakao access token refreshed.")
    return data["access_token"]


def _post_memo(template: dict, access_token: str) -> requests.Response:
    return requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/x-www-form-urlencoded",
        },
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=15,
    )


def _send(template: dict):
    """Send one Kakao memo, refreshing the token once on 401."""
    cfg  = _cfg()
    resp = _post_memo(template, cfg["access_token"])
    if resp.status_code == 401:
        new_token = _refresh_access_token()
        resp = _post_memo(template, new_token)
    if resp.status_code != 200:
        raise RuntimeError(f"KakaoTalk error {resp.status_code}: {resp.text}")


def send_text(text: str):
    """Send a plain-text memo (up to 10000 bytes)."""
    _send(
        {
            "object_type": "text",
            "text": text[:10000],
            "link": {
                "web_url":        "https://arxiv.org",
                "mobile_web_url": "https://arxiv.org",
            },
        }
    )


def send_feed(title: str, description: str, url: str, button_label: str = "논문 보기"):
    """Send a feed-type memo (title ≤ 400, description ≤ 400 chars)."""
    _send(
        {
            "object_type": "feed",
            "content": {
                "title":       title[:400],
                "description": description[:400],
                "link": {
                    "web_url":        url,
                    "mobile_web_url": url,
                },
            },
            "buttons": [
                {
                    "title": button_label,
                    "link": {
                        "web_url":        url,
                        "mobile_web_url": url,
                    },
                }
            ],
        }
    )


def send_papers(results: list[tuple[dict, str]], form_url: str = ""):
    """Send each paper as a plain-text memo."""
    if not results:
        return
    date  = results[0][0]["published"]
    count = len(results)
    intro = f"📚 오늘의 논문 ({date})\n총 {count}편 — robotics / RL / world model / VLA"
    if form_url:
        intro += f"\n\n⭐ 별점 입력 (폼): {form_url}"
    send_text(intro)

    for i, (paper, summary) in enumerate(results, 1):
        authors = ", ".join(paper["authors"])
        if paper.get("more_authors", 0):
            authors += f" 외 {paper['more_authors']}명"
        msg = (
            f"[{i}/{count}] {paper['title']}\n"
            f"✍  {authors}\n"
            f"📅 {paper['published']}\n\n"
            f"{summary}\n\n"
            f"🔗 {paper['url']}"
        )
        send_text(msg)
