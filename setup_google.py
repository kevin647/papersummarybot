"""
One-time Google OAuth setup for Forms API access.

Run:  python setup_google.py

A browser will open for Google login.
After you authorize, the token is saved to google_token.pickle automatically.

Before running this script, download OAuth2 credentials:
  1. https://console.cloud.google.com 접속
  2. 새 프로젝트 생성 (또는 기존 선택)
  3. API 및 서비스 → 라이브러리 → 'Google Forms API' 검색 → 사용 설정
  4. API 및 서비스 → OAuth 동의 화면 → 외부 선택 → 앱 이름/이메일 입력 후 저장
  5. API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 2.0 클라이언트 ID
  6. 애플리케이션 유형: 데스크톱 앱 → 만들기
  7. JSON 다운로드 → 이 폴더에 google_credentials.json 으로 저장
  8. python setup_google.py 실행
"""
from pathlib import Path

_CREDS_PATH = Path(__file__).parent / "google_credentials.json"

if __name__ == "__main__":
    print("=== Google OAuth Setup ===\n")

    if not _CREDS_PATH.exists():
        print(
            "google_credentials.json 파일이 없습니다.\n\n"
            "아래 순서로 생성하세요:\n"
            "  1. https://console.cloud.google.com 접속\n"
            "  2. 새 프로젝트 생성 (또는 기존 선택)\n"
            "  3. API 및 서비스 → 라이브러리 → 'Google Forms API' 검색 → 사용 설정\n"
            "  4. API 및 서비스 → OAuth 동의 화면 → 외부 → 앱 이름/이메일 입력 저장\n"
            "  5. 사용자 인증 정보 → 만들기 → OAuth 2.0 클라이언트 ID → 데스크톱 앱\n"
            "  6. JSON 다운로드 → google_credentials.json 으로 이 폴더에 저장\n"
            "  7. python setup_google.py 다시 실행\n"
        )
        raise SystemExit("google_credentials.json 을 먼저 준비해주세요.")

    from form_manager import _get_creds
    print("브라우저에서 Google 계정으로 로그인하세요...\n")
    _get_creds()
    print("✅ Google 인증 완료!")
    print("   토큰 저장됨: google_token.pickle")
    print("\n이제 main.py 실행 시 자동으로 Google Form이 생성됩니다.")
