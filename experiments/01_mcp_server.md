# 실험 01: MCP 서버 만들기

## 과제 목표

지난 lec06_harness 프로젝트에서 "이거 자동화됐으면" 했던 병목을 MCP 서버로 직접 구현한다.

## 현재 병목 분석

`app/main.py`에서 발견한 3가지 병목:

| 병목 | 코드 위치 | 문제 |
|------|----------|------|
| YouTube 자막 추출 | `main.py:327-616` | 200줄 넘는 폴백 체인 (InnerTube → yt-dlp API → CLI → youtube-transcript-api). 에이전트가 직접 호출 불가 |
| 밈 번역 | `main.py:55-105` | System prompt가 하드코딩. 에이전트가 번역 파이프라인을 tool로 호출할 수 없음 |
| 강의 분석 | `main.py:107-168` | 자막 → 지식베이스 → Q&A 3단계가 API 엔드포인트에 묶여 있어 에이전트가 단계별 제어 불가 |

## 해결: MCP 서버 3개 Tool

### Tool 1: `youtube_transcript`
- **기능**: YouTube URL → 자막 텍스트 반환
- **입력**: `{"url": "https://youtube.com/watch?v=..."}`
- **출력**: `{"transcript": "...", "video_id": "...", "language": "ko"}`
- **기존 대비 개선**: 200줄 폴백 로직을 tool 1개로 캡슐화. 에이전트가 자막 추출을 독립적으로 호출 가능

### Tool 2: `meme_translate`
- **기능**: 해외 밈/슬랭 → 한국 신조어 초월번역
- **입력**: `{"text": "It's giving main character energy"}`
- **출력**: `{"original": "...", "candidates": [...], "final": {"translation": "..."}}`
- **기존 대비 개선**: 번역 결과를 구조화된 JSON으로 반환. 에이전트가 후보 중 선택 가능

### Tool 3: `lecture_analyze`
- **기능**: 강의 자막 → 구조화된 지식베이스 생성
- **입력**: `{"transcript": "..."}`
- **출력**: `{"title": "...", "sections": [...], "key_concepts": [...], "faq": [...]}`
- **기존 대비 개선**: 분석 결과를 에이전트가 받아서 Q&A, 요약 등 후속 작업에 활용 가능

## 아키텍처

```
Hermes Agent (Kaggle vLLM / Qwen2.5-7B)
    │
    ├── MCP Server (Python, mcp SDK)
    │   ├── youtube_transcript  ← InnerTube/yt-dlp 폴백 로직 래핑
    │   ├── meme_translate      ← LLM 호출 + 3단계 파이프라인
    │   └── lecture_analyze     ← LLM 호출 + 지식베이스 구축
    │
    └── OpenAI-compatible API
        └── Kaggle vLLM (Cloudflare Tunnel)
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| MCP SDK | `mcp[cli]` (Python) |
| 전송 방식 | stdio (로컬) / SSE (원격) |
| LLM 백엔드 | Kaggle vLLM (Qwen2.5-7B-AWQ) 또는 Groq |
| 자막 추출 | youtube-transcript-api, yt-dlp (폴백) |

## 파일 구조

```
experiments/
├── 01_mcp_server.md          ← 이 문서
├── mcp_server/
│   ├── server.py             ← MCP 서버 (정상 버전)
│   ├── server_broken.py      ← MCP 서버 (의도적 실패 버전 - 실험02용)
│   ├── requirements.txt
│   └── config.json           ← Claude Desktop/Agent 연결 설정
├── 02_success_fail/
│   ├── run.py                ← 실험02 실행 스크립트
│   └── results.md            ← 비교 결과표
└── 03_orchestration/
    ├── run.py                ← 실험03 실행 스크립트
    └── results.md            ← 벤치마크 결과표
```

## 실행 방법

```bash
# 1. 의존성 설치
cd experiments/mcp_server
pip install -r requirements.txt

# 2. 환경변수 설정
export VLLM_BASE_URL="https://xxx-yyy.trycloudflare.com/v1"  # Kaggle URL
# 또는 Groq 사용 시:
export GROQ_API_KEY="your_key"

# 3. MCP 서버 단독 테스트
python server.py

# 4. Claude Desktop에 연결 (config.json 참고)
```

## 산출물

- [x] GitHub 저장소에 MCP 서버 코드
- [ ] 동작 데모 영상 30초
- [ ] 실험 02, 03 결과와 연계
