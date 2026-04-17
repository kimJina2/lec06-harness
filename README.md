# Harness AI 🌸

해외 밈·슬랭을 한국 신조어로 초월번역하고, 해외 강의를 AI 러닝 파트너로 바꿔주는 웹 앱입니다.

🔗 **배포 주소**: https://lec06-harness.onrender.com

---

## 기능

### 🌐 밈 초월번역기
해외 인터넷 밈·슬랭·유행어를 단순 번역이 아닌 **한국 최신 신조어**로 감정 톤까지 살려 번역합니다.

- 영어권·일본어권 밈 맥락 분석
- 동일한 감정 톤의 한국 신조어 매핑
- 혐오·비하 표현 자동 필터링
- 3단계 파이프라인: Slang-Decoder → Trend-Monitor → Sensitivity-Checker

### 🎓 강의 인터랙티브 Q&A
해외 대학 강의·기술 세미나 자막을 분석해 **강의 내용을 근거로 답변하는 AI 러닝 파트너**입니다.

- YouTube 영상 자막 자동 추출 또는 텍스트 직접 붙여넣기
- 강의 핵심 개념·요약 자동 생성
- 중요도별 FAQ 추출 (핵심 / 중요 / 참고)
- 강의 내용 기반 Q&A 대화

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| 백엔드 | Python, FastAPI, uvicorn |
| 프론트엔드 | React, Vite |
| AI | OpenRouter (Claude Haiku 4.5) |
| 배포 | Render (Web Service) |

---

## 로컬 실행

```bash
# 백엔드
cd app
pip install -r requirements.txt
GROQ_API_KEY=your_key uvicorn main:app --host 0.0.0.0 --port 8080

# 프론트엔드 (별도 터미널)
cd app/frontend-react
npm install
npm run dev
```

로컬에서는 Groq API (무료)를 기본으로 사용합니다. [Groq 콘솔](https://console.groq.com)에서 키를 발급받으세요.

---

## 환경변수 (Render 배포 시)

| 변수 | 설명 |
|------|------|
| `APP_ENV` | `production` 으로 설정 |
| `OPENROUTER_API_KEY` | OpenRouter API 키 |
