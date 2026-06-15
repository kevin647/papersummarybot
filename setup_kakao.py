"""
One-time KakaoTalk OAuth setup.

Run:  python setup_kakao.py

A browser will open for KakaoTalk login.  After you authorize,
the access & refresh tokens are saved to .env automatically.
You only need to run this once (refresh tokens last 60 days).
"""
import os
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

_ENV_PATH    = Path(__file__).parent / ".env"
_REDIRECT_URI = "http://localhost:5000/callback"

# Module-level variable populated by the callback handler
_auth_code: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            _auth_code = params["code"][0]
            body       = b"<h2>Authorization complete. You can close this tab.</h2>"
            self.send_response(200)
        else:
            body = b"<h2>Authorization failed - no code received.</h2>"
            self.send_response(400)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass  # suppress console noise


def _authorize(rest_api_key: str, client_secret: str = "") -> tuple[str, str]:
    """Open browser → capture auth code → exchange for tokens."""
    auth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={rest_api_key}"
        f"&redirect_uri={urllib.parse.quote(_REDIRECT_URI, safe='')}"
        "&response_type=code"
        "&scope=talk_message"
    )
    print(f"\nOpening browser for KakaoTalk login…")
    print(f"If it does not open automatically, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for exactly one redirect from the browser
    HTTPServer(("localhost", 5000), _CallbackHandler).handle_request()

    if not _auth_code:
        raise SystemExit("No authorization code was received.")

    token_data = {
        "grant_type":   "authorization_code",
        "client_id":    rest_api_key,
        "redirect_uri": _REDIRECT_URI,
        "code":         _auth_code,
    }
    if client_secret:
        token_data["client_secret"] = client_secret
    resp = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data=token_data,
        timeout=15,
    )
    data = resp.json()
    if "access_token" not in data:
        raise SystemExit(f"Token exchange failed: {data}")

    return data["access_token"], data["refresh_token"]


if __name__ == "__main__":
    print("=== Kakao OAuth Setup ===\n")

    if not _ENV_PATH.exists():
        raise SystemExit(
            ".env not found.\n"
            "Copy .env.example to .env and fill in GEMINI_API_KEY and KAKAO_REST_API_KEY first."
        )

    load_dotenv(_ENV_PATH)
    rest_api_key  = os.getenv("KAKAO_REST_API_KEY", "")
    client_secret = os.getenv("KAKAO_CLIENT_SECRET", "")
    if not rest_api_key or rest_api_key == "your_kakao_rest_api_key_here":
        raise SystemExit("KAKAO_REST_API_KEY is not set in .env — please add it first.")

    access_token, refresh_token = _authorize(rest_api_key, client_secret)

    set_key(str(_ENV_PATH), "KAKAO_ACCESS_TOKEN",  access_token)
    set_key(str(_ENV_PATH), "KAKAO_REFRESH_TOKEN", refresh_token)

    print(f"\nTokens saved to .env")
    print(f"  access_token  : {access_token[:24]}…")
    print(f"  refresh_token : {refresh_token[:24]}…")
    print("\nSetup complete!  You can now run:  python main.py")
