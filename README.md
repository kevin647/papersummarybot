# arXiv 논문 알리미 📚

arXiv에 새로 올라온 논문을 Gemini가 매일 한국어로 요약해서 **카카오톡 나에게 보내기**로 전송해주는 자동화 도구입니다.


- 매일 아침 어제 날짜 논문을 자동 수집 · 요약 · 전송
- 요약본과 PDF를 `paper/{날짜}/` 폴더에 저장
- 구글 폼 링크를 카카오톡으로 전송 → 폰에서 논문별 별점(1~5점) 입력
- 별점 응답을 자동으로 MD 파일에 반영
- 컴퓨터 시작 시 백그라운드 자동 실행 (Windows 작업 스케줄러)

---

## Project structure

```
.
├── main.py             ← 진입점 (스케줄러)
├── arxiv_client.py     ← arXiv API 논문 수집
├── summarizer.py       ← Gemini 한국어 요약
├── kakao_notifier.py   ← 카카오톡 메시지 전송
├── form_manager.py     ← 구글 폼 생성 · 응답 수집
├── paper_saver.py      ← PDF 다운로드 · MD 저장
├── setup_kakao.py      ← 카카오 OAuth 최초 인증
├── setup_google.py     ← 구글 OAuth 최초 인증
├── setup_autostart.py  ← Windows 자동시작 등록
├── config.py           ← 모든 설정값
├── requirements.txt
└── .env                ← API 키 (절대 커밋 금지)
```

---

## 설치 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. `.env` 파일 생성

```bash
copy .env.example .env
```

`.env`를 열고 아래 값을 채워주세요:

| 키 | 발급 방법 |
|----|-----------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) → API 키 발급 |
| `KAKAO_REST_API_KEY` | [Kakao Developers](https://developers.kakao.com) → 내 애플리케이션 → 앱 키 → **REST API 키** |

### 3. 카카오 앱 설정 (최초 1회)

> ⚠️ 2026-06-16 기준 최신 UI — 카카오 디벨로퍼스가 대대적으로 개편되어 기존 '플랫폼' 메뉴가 삭제됐습니다.

1. [developers.kakao.com](https://developers.kakao.com) 로그인 → **내 애플리케이션 → 애플리케이션 추가**

2. **REST API 키 확인 + Redirect URI 등록**
   - **[앱 설정] → [플랫폼 키]** (예전 '플랫폼' 메뉴를 대체)
   - REST API 키 복사 → `.env`에 입력
   - 해당 키의 **[설정]** 버튼 → [카카오 로그인 리다이렉트 URI]에 `http://localhost:5000/callback` 추가

3. **웹 도메인 등록**
   - **[앱 설정] → [제품 링크 관리] → [웹 도메인]** → `http://localhost:5000` 추가

4. **카카오 로그인 활성화**
   - **[제품 설정] → [카카오 로그인] → [일반]** → 활성화 **ON**

5. **동의항목 설정**
   - **[제품 설정] → [카카오 로그인] → [동의항목]**
   - 하단 **[접근권한]** 목록 → **카카오톡 메시지 전송** → [설정] → 동의 단계 선택 후 저장

6. **(선택) Client Secret 비활성화 권장**
   - **[제품 설정] → [카카오 로그인] → [보안]**
   - 로컬 테스트 환경이라면 **"사용 안 함"으로 끄는 것을 강력 권장**
   - 켜두려면 코드를 복사해서 `.env`에 `KAKAO_CLIENT_SECRET=코드` 추가

### 4. 카카오 인증 (최초 1회)

```bash
python setup_kakao.py
```

### 5. (선택) 구글 폼 연동 — 폰에서 별점 입력

> ⚠️ 2026-06-16 기준 최신 UI

1. [console.cloud.google.com](https://console.cloud.google.com) → 프로젝트 생성  
   (화면 상단 'Google Cloud' 로고 옆에서 프로젝트 선택 확인)
2. **☰ → [API 및 서비스] → [라이브러리]** → `Google Forms API` 검색 → 사용 설정
3. **☰ → [API 및 서비스] → [OAuth 동의 화면]** → 외부 선택 → 앱 이름/이메일 입력 후 저장
4. 좌측 메뉴 **[대상]** 클릭 → 스크롤 내려 **[테스트 사용자]** 섹션 → **[+ ADD USERS]** → 본인 이메일 추가
5. **☰ → [API 및 서비스] → [사용자 인증 정보]** → **[+ 사용자 인증 정보 만들기]** → OAuth 2.0 클라이언트 ID → 데스크톱 앱 → JSON 다운로드
6. 다운받은 파일을 `google_credentials.json`으로 프로젝트 폴더에 저장
7. `python setup_google.py` 실행

---

## 실행

```bash
python main.py
```

- 어제 날짜 요약이 없으면 **즉시 실행**
- 이후 매일 **08:00** 자동 반복 (변경 가능)
- 매 1시간마다 구글 폼 응답을 체크해 MD 별점 업데이트

---

## 주제 / 키워드 변경

`config.py`를 열어 수정하세요:

```python
# 검색 키워드 — 관심 분야에 맞게 추가/삭제
SEARCH_KEYWORDS = [
    "robotics",
    "reinforcement learning",
    "world model",
    "VLA",
    "vision language action",
    "navigation",
    "SLAM",
]

# arXiv 카테고리 — https://arxiv.org/category_taxonomy 참고
ARXIV_CATEGORIES = ["cs.RO", "cs.LG", "cs.AI", "cs.CV", "cs.CL"]

# 하루에 받을 논문 수
MAX_PAPERS_PER_DAY = 5

# 매일 실행 시각 (24시간제, 로컬 시간)
DAILY_RUN_TIME = "08:00"
```

---

## 요약 프롬프트 변경

요약 형식이나 말투를 바꾸고 싶으면 `summarizer.py`를 열어 두 곳을 수정하세요:

**1) 시스템 프롬프트** — Gemini의 기본 역할/말투 설정 (`_SYSTEM_PROMPT`)

```python
_SYSTEM_PROMPT = (
    "너는 논문 요약 전문가야. "
    "무조건 짧고 직접적으로 말해. "
    "한국어로만 답해."
    # 원하는 지시사항 추가 가능
)
```

**2) 요약 형식** — 각 논문에 보내는 실제 프롬프트 (`summarize_paper` 함수 내)

```python
"위 논문을 아래 형식으로 요약해. 각 항목은 2~3문장 이내로만.\n\n"
"(1) 한줄요약: 이 논문이 뭔지 한 문장으로.\n"
"(2) 기여점: 이 논문이 뭘 새로 했는지.\n"
"(3) 구현방법: 어떻게 만들었는지 짧게."
# 항목 추가/삭제/수정 자유
```

---

## 전체 설정값 (`config.py`)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SEARCH_KEYWORDS` | robotics, RL, world model … | arXiv 검색 키워드 |
| `ARXIV_CATEGORIES` | cs.RO, cs.LG, cs.AI, cs.CV, cs.CL | arXiv 카테고리 |
| `MAX_PAPERS_PER_DAY` | `5` | 하루 최대 논문 수 |
| `DAILY_RUN_TIME` | `"08:00"` | 실행 시각 |
| `GEMINI_MODEL` | `"gemini-3.1-pro-preview"` | Gemini 모델 |
| `PAPER_SAVE_DIR` | `"paper"` | 저장 폴더 (구글 드라이브 경로로 변경 가능) |

---

## Windows 자동시작 설정

```bash
python setup_autostart.py
```

로그인할 때마다 백그라운드에서 자동 실행됩니다.  
해제하려면: `python setup_autostart.py --unregister`

---

## 토큰 갱신

카카오톡 액세스 토큰은 **6시간**마다 자동 갱신됩니다.  
리프레시 토큰은 **60일** 후 만료 — `python setup_kakao.py` 재실행으로 갱신.
