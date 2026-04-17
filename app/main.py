import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import re
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

app = FastAPI(title="Harness Web App")

# ── 환경 설정 ─────────────────────────────────────────────────────────────────
# 로컬: APP_ENV=local  → Ollama (무료, 로컬 실행)
# 배포: APP_ENV=production → OpenRouter (Claude)

APP_ENV = os.environ.get("APP_ENV", "local")

if APP_ENV == "production":
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    )
    MODEL = "anthropic/claude-haiku-4-5"
else:
    # 로컬: Groq (무료, 빠름 — https://console.groq.com 에서 키 발급)
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY", ""),
    )
    MODEL = "llama-3.1-8b-instant"

print(f"[설정] 환경={APP_ENV} | 모델={MODEL}")

# ── System Prompts ────────────────────────────────────────────────────────────
# 로컬(Groq 무료)용 — 토큰 절약을 위해 간결하게

MEME_SYSTEM_LOCAL = """해외 밈/슬랭을 한국 신조어로 초월번역해. 반드시 아래 JSON만 출력:
{"original":"원문","analysis":{"literal":"직역","real_meaning":"실제의미","tone":"감정톤"},"candidates":[{"text":"후보1","reason":"이유"},{"text":"후보2","reason":"이유"},{"text":"후보3","reason":"이유"}],"final":{"translation":"최종번역","grade":"통과","note":"검수노트","platforms":{"youtube_general":true,"youtube_adult":true,"tiktok_instagram":true}}}"""

LECTURE_ANALYZE_SYSTEM_LOCAL = """강의 자막을 분석해 한국어로 요약하고 아래 JSON만 출력. faq는 중요도(HIGH/MEDIUM/LOW)별로 최대 10개:
{"title":"제목","language":"언어","summary":"200자요약","sections":[{"index":1,"topic":"주제","content":"내용","key_terms":["용어"],"importance":"HIGH"}],"key_concepts":[{"concept":"개념","definition":"정의","related_to":[],"importance":"HIGH"}],"faq":[{"question":"질문","answer_hint":"힌트","importance":"HIGH"}],"learning_path":["개념1","개념2"]}"""

LECTURE_QA_SYSTEM_LOCAL = """강의 내용 기반 조교야. 지식 베이스를 참고해 질문에 답해. 강의에 없는 내용은 솔직히 말해."""



MEME_SYSTEM = """당신은 글로벌 밈·슬랭 초월번역 전문가 팀입니다.
입력된 해외 밈·슬랭을 아래 3단계 파이프라인으로 분석하고, 최종 번역 결과를 JSON으로 반환하세요.

## Phase 1 — Slang Decoder (맥락·뉘앙스 분석)
- 원래 의미, 문화적 배경, 감정 톤(유머/비꼼/감탄/공감/자조), 번역 장벽 파악
- 직역하면 왜 어색한지 명확히 기록

## Phase 2 — Trend Monitor (한국 신조어 매핑)
- Phase 1 감정 톤과 동일한 최신 한국 유행어·신조어 3개 후보 제시
- 각 후보에 선택 이유 포함

## Phase 3 — Sensitivity Checker (검수)
- 후보 중 혐오·비하·과도한 비속어 여부 확인
- 최종 번역 1개 선정 + 검수 등급(통과/주의/수정됨) + 플랫폼 가능 여부

최종 출력은 반드시 아래 JSON 형식만 반환하세요 (설명 텍스트 없이):
{
  "original": "원문",
  "analysis": {
    "literal": "직역",
    "real_meaning": "실제 의미 (뉘앙스 포함)",
    "origin": "유래·출처 플랫폼",
    "tone": "감정 톤",
    "translation_barrier": "직역 실패 이유"
  },
  "candidates": [
    {"text": "후보1", "reason": "선택 이유"},
    {"text": "후보2", "reason": "선택 이유"},
    {"text": "후보3", "reason": "선택 이유"}
  ],
  "final": {
    "translation": "최종 번역",
    "grade": "통과|주의|수정됨",
    "note": "검수 노트",
    "platforms": {
      "youtube_general": true,
      "youtube_adult": true,
      "tiktok_instagram": true
    }
  }
}"""

LECTURE_ANALYZE_SYSTEM = """당신은 해외 강의·세미나 자막을 분석하는 전문가 팀입니다.
아래 2단계 파이프라인으로 자막을 분석하고 지식 베이스를 구축하세요.

## Phase 1 — Transcription Agent (자막 구조화)
- 자막 텍스트를 주제 단위 섹션으로 분절
- 각 섹션의 핵심 개념·용어·정의 추출
- 강사가 반복·강조한 내용에 HIGH 중요도 부여

## Phase 2 — Knowledge Graph Builder (지식 베이스 구축)
- 개념 간 관계 정의 (정의·예시·대비·선행개념·응용)
- 학습자가 자주 묻는 FAQ 3~5개 사전 생성
- 강의 전체 계층형 요약

최종 출력은 반드시 아래 JSON 형식만 반환하세요 (설명 텍스트 없이):
{
  "title": "강의 제목 추론",
  "language": "강의 언어",
  "summary": "강의 전체 핵심 내용 200자 요약",
  "sections": [
    {
      "index": 1,
      "topic": "섹션 주제",
      "content": "핵심 내용",
      "key_terms": ["용어1", "용어2"],
      "importance": "HIGH|MEDIUM|LOW"
    }
  ],
  "key_concepts": [
    {
      "concept": "개념명",
      "definition": "한국어 정의",
      "related_to": ["관련개념"],
      "importance": "HIGH|MEDIUM"
    }
  ],
  "faq": [
    {"question": "예상 질문", "answer_hint": "핵심 포인트", "importance": "HIGH|MEDIUM|LOW"}
  ],
  "learning_path": ["선행개념", "핵심개념", "응용개념"]
}"""

LECTURE_QA_SYSTEM = """당신은 강의 내용을 완전히 숙지한 조교이자 러닝 파트너입니다.
제공된 강의 지식 베이스와 원본 자막을 근거로 사용자 질문에 답변하세요.

## 답변 원칙
1. 강의에서 설명된 방식으로 먼저 답변
2. 강의 외 추가 지식은 "강의 외 내용:" 접두어로 분리
3. 질문에 잘못된 전제가 있으면 먼저 바로잡기
4. 답변 마지막에 관련 심화 질문 1개 제안

## 답변 형식
**핵심 답변**
[1~2문장 직접 답변]

**강의 설명**
[강의 내용 기반 상세 설명]

**예시** (해당하는 경우)
[강의에서 제시된 예시]

💡 **더 알아보려면**: [후속 질문 제안]

강의에 없는 내용이면: "이 강의에서는 다루지 않았습니다."라고 솔직히 알려주세요."""


# ── Request Models ────────────────────────────────────────────────────────────

class MemeRequest(BaseModel):
    text: str

class YouTubeRequest(BaseModel):
    url: str

class LectureAnalyzeRequest(BaseModel):
    transcript: str

class LectureAskRequest(BaseModel):
    transcript: str
    knowledge: str
    history: list[dict]
    question: str


# ── Streaming Helpers ─────────────────────────────────────────────────────────

async def stream_claude(system: str, user_message: str):
    """Yield SSE lines from an OpenRouter streaming call."""
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _run_in_thread():
        try:
            stream = client.chat.completions.create(
                model=MODEL,
                max_tokens=4096,
                stream=True,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
            )
            full_text = ""
            for chunk in stream:
                text = chunk.choices[0].delta.content or ""
                if text:
                    full_text += text
                    loop.call_soon_threadsafe(queue.put_nowait, ("chunk", text))
            loop.call_soon_threadsafe(queue.put_nowait, ("done", full_text))
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))

    import threading
    thread = threading.Thread(target=_run_in_thread, daemon=True)
    thread.start()

    while True:
        kind, value = await queue.get()
        if kind == "chunk":
            data = json.dumps({"chunk": value}, ensure_ascii=False)
            yield f"data: {data}\n\n"
        elif kind == "done":
            yield f"data: {json.dumps({'done': True, 'full': value}, ensure_ascii=False)}\n\n"
            break
        elif kind == "error":
            yield f"data: {json.dumps({'error': value}, ensure_ascii=False)}\n\n"
            break


# ── API Routes ────────────────────────────────────────────────────────────────

@app.post("/api/meme-translate")
async def meme_translate(req: MemeRequest):
    system = MEME_SYSTEM_LOCAL if APP_ENV == "local" else MEME_SYSTEM
    async def generate():
        async for line in stream_claude(system, f"번역: {req.text}"):
            yield line
    return StreamingResponse(generate(), media_type="text/event-stream")


def _extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)",
        r"youtube\.com/embed/([^&\n?#]+)",
        r"youtube\.com/shorts/([^&\n?#]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


@app.post("/api/lecture/youtube")
async def fetch_youtube_transcript(req: YouTubeRequest):
    video_id = _extract_video_id(req.url)
    if not video_id:
        return {"error": "유효하지 않은 YouTube URL입니다."}

    loop = asyncio.get_event_loop()
    try:
        def _fetch():
            api = YouTubeTranscriptApi()
            # 한국어 → 영어 순서로 시도, 없으면 목록에서 첫 번째 자막 사용
            try:
                return api.fetch(video_id, languages=["ko", "en"])
            except NoTranscriptFound:
                transcript_list = api.list(video_id)
                transcript = next(iter(transcript_list))
                return transcript.fetch()


        segments = await loop.run_in_executor(None, _fetch)
        text = " ".join(s.text.replace("\n", " ") for s in segments)
        return {"transcript": text, "video_id": video_id}

    except TranscriptsDisabled:
        return {"error": "이 영상은 자막이 비활성화되어 있습니다."}
    except Exception as e:
        return {"error": f"자막을 가져올 수 없습니다: {str(e)}"}


@app.post("/api/lecture/analyze")
async def lecture_analyze(req: LectureAnalyzeRequest):
    if APP_ENV == "local":
        system = LECTURE_ANALYZE_SYSTEM_LOCAL
        MAX_CHARS = 2000   # 토큰 절약: 약 500토큰
    else:
        system = LECTURE_ANALYZE_SYSTEM
        MAX_CHARS = 60000

    transcript = req.transcript[:MAX_CHARS]
    truncated = len(req.transcript) > MAX_CHARS

    async def generate():
        if truncated:
            notice = json.dumps({"chunk": f"[로컬 모드: 앞 {MAX_CHARS:,}자만 분석]\n\n"}, ensure_ascii=False)
            yield f"data: {notice}\n\n"
        async for line in stream_claude(system, f"자막:\n{transcript}"):
            yield line
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/lecture/ask")
async def lecture_ask(req: LectureAskRequest):
    history_text = "\n".join(
        f"{'학습자' if m['role'] == 'user' else '조교'}: {m['content']}"
        for m in req.history[-4:]  # 로컬에서 히스토리 최소화
    )
    MAX_KB = 1500 if APP_ENV == "local" else 20000
    knowledge = req.knowledge[:MAX_KB]
    system = LECTURE_QA_SYSTEM_LOCAL if APP_ENV == "local" else LECTURE_QA_SYSTEM

    user_prompt = f"""지식베이스:{knowledge}
대화:{history_text or '없음'}
질문:{req.question}"""

    async def generate():
        async for line in stream_claude(system, user_prompt):
            yield line
    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Static Files & Root ───────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

@app.get("/introduce")
async def introduce_page():
    return FileResponse("frontend/introduce.html")

@app.get("/meme")
async def meme_page():
    return FileResponse("frontend/meme.html")

@app.get("/lecture")
async def lecture_page():
    return FileResponse("frontend/lecture.html")
