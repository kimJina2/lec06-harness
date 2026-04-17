import os
import sys
import json
import asyncio
import shutil
import subprocess
import tempfile
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import re
from urllib.parse import urlparse, parse_qs
from openai import OpenAI
import requests

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
    MODEL = "anthropic/claude-haiku-4.5"
else:
    # 로컬: Groq (무료, 빠름 — https://console.groq.com 에서 키 발급)
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY", ""),
    )
    MODEL = "llama-3.1-8b-instant"

print(f"[설정] 환경={APP_ENV} | 모델={MODEL}")

# YouTube 쿠키 파일 (YOUTUBE_COOKIES 환경변수 → 임시 파일로 저장)
COOKIES_FILE: str | None = None
_cookies_raw = os.environ.get("YOUTUBE_COOKIES", "").strip()
if _cookies_raw:
    _cf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    _cf.write(_cookies_raw)
    _cf.close()
    COOKIES_FILE = _cf.name
    print(f"[설정] YouTube 쿠키 로드됨 → {COOKIES_FILE}")

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
    if not url:
        return None

    url = url.strip()
    if not url:
        return None

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
        url = 'https://' + url

    parsed = urlparse(url)
    hostname = (parsed.hostname or '').lower()
    path = parsed.path or ''

    if hostname.endswith('youtu.be'):
        video_id = path.lstrip('/').split('/')[0]
        return video_id or None

    if 'youtube.com' in hostname or 'youtube-nocookie.com' in hostname:
        query = parse_qs(parsed.query)
        if query.get('v'):
            return query['v'][0]

        path_segments = [segment for segment in path.split('/') if segment]
        if len(path_segments) >= 2 and path_segments[0] in ('embed', 'shorts'):
            return path_segments[1]

    return None


def _get_default_proxy_url() -> str | None:
    return (
        os.environ.get('TRANSCRIPT_PROXY')
        or os.environ.get('YOUTUBE_TRANSCRIPT_PROXY')
        or os.environ.get('HTTPS_PROXY')
        or os.environ.get('https_proxy')
        or os.environ.get('HTTP_PROXY')
        or os.environ.get('http_proxy')
    )


def _build_proxy_dict() -> dict[str, str] | None:
    proxies: dict[str, str] = {}
    default_proxy = _get_default_proxy_url()
    if default_proxy:
        proxies['http'] = default_proxy
        proxies['https'] = default_proxy

    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if http_proxy:
        proxies['http'] = http_proxy
    if https_proxy:
        proxies['https'] = https_proxy

    return proxies or None


def _parse_vtt(content: str) -> str:
    """VTT 자막 파일을 평문으로 변환."""
    texts = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:", "X-TIMESTAMP")):
            continue
        if "-->" in line or re.match(r"^\d+$", line):
            continue
        text = re.sub(r"<[^>]+>", "", line)
        text = re.sub(r"&amp;", "&", text).replace("&lt;", "<").replace("&gt;", ">").strip()
        if text:
            texts.append(text)
    deduped: list[str] = []
    for t in texts:
        if not deduped or deduped[-1] != t:
            deduped.append(t)
    return " ".join(deduped)


def _fetch_transcript_innertube(video_id: str) -> str:
    """YouTube InnerTube API로 자막 요청 (Android 클라이언트 위장)."""
    url = "https://www.youtube.com/youtubei/v1/get_transcript"

    headers = {
        "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11; en_US) gzip",
        "Content-Type": "application/json",
    }

    data = {
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "19.09.37",
                "osName": "Android",
                "osVersion": "11",
            }
        },
        "params": f"CgIQBg%3D%3D",
    }

    proxies = _build_proxy_dict()
    try:
        # captionTracks 얻기 위해 초기 요청
        init_url = f"https://www.youtube.com/watch?v={video_id}&hl=en"
        session = requests.Session()
        if proxies:
            session.proxies.update(proxies)

        resp = session.get(init_url, headers={"User-Agent": headers["User-Agent"]}, timeout=10)

        # ytInitialData에서 captionTracks 추출
        match = re.search(r'"captions":\{"playerCaptionsTracklistRenderer":\{"captionTracks":\s*\[(.*?)\]', resp.text)
        if not match:
            match = re.search(r'"captionTracks":\s*\[(.*?)\]', resp.text)

        if not match:
            raise ValueError("자막을 찾을 수 없습니다")

        captions_str = "[" + match.group(1) + "]"
        captions = json.loads(captions_str)

        if not captions:
            raise ValueError("이 영상에서 자막을 찾을 수 없습니다")

        # 언어 우선순위: 한국어 > 영어 > 기타
        def lang_priority(cap: dict) -> int:
            lang = cap.get("languageCode", "").lower()
            if lang.startswith("ko"):
                return 0
            if lang.startswith("en"):
                return 1
            return 2

        captions.sort(key=lang_priority)
        caption_url = captions[0].get("baseUrl")

        if not caption_url:
            raise ValueError("자막 URL을 찾을 수 없습니다")

        # VTT 자막 다운로드
        vtt_resp = session.get(caption_url, timeout=10)
        vtt_resp.raise_for_status()

        return _parse_vtt(vtt_resp.text)

    except requests.RequestException as e:
        msg = str(e)
        if proxies:
            raise ValueError(
                f"자막 요청 실패: {msg}. 프록시를 사용 중입니다. 클라우드 IP 차단일 수 있습니다."
            )
        raise ValueError(
            f"자막 요청 실패: {msg}. 클라우드 IP 차단일 수 있습니다. TRANSCRIPT_PROXY/HTTP_PROXY/HTTPS_PROXY 환경변수로 프록시를 지정해보세요."
        )
    except (json.JSONDecodeError, KeyError, AttributeError):
        raise ValueError("자막 데이터 파싱 실패")


def _fetch_transcript_ytdlp(url: str) -> tuple[str, str]:
    """yt-dlp Python API로 자막 다운로드. 실패 시 CLI 또는 youtube-transcript-api로 폴백."""
    video_id = _extract_video_id(url) or "unknown"

    try:
        import yt_dlp
        try:
            return _fetch_transcript_ytdlp_api(url, video_id, yt_dlp)
        except Exception as e1:
            print(f"[yt-dlp Python API 실패] {e1}", flush=True)
            if shutil.which("yt-dlp"):
                try:
                    return _fetch_transcript_ytdlp_cli(url, video_id)
                except Exception as e2:
                    print(f"[yt-dlp CLI 실패] {e2}", flush=True)
                    return _fetch_transcript_youtube_api(video_id)
            return _fetch_transcript_youtube_api(video_id)
    except ModuleNotFoundError:
        if shutil.which("yt-dlp"):
            return _fetch_transcript_ytdlp_cli(url, video_id)
        return _fetch_transcript_youtube_api(video_id)


def _fetch_transcript_ytdlp_api(url: str, video_id: str, yt_dlp_module) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_tmpl = os.path.join(tmpdir, "%(id)s.%(ext)s")
        ydl_opts = {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["all"],
            "subtitlesformat": "vtt",
            "skip_download": True,
            "outtmpl": out_tmpl,
            "quiet": APP_ENV != "production",
            "no_warnings": APP_ENV != "production",
            "ignoreerrors": False,
            # 클라우드 IP 차단 우회: TV/iOS 클라이언트는 web 클라이언트보다 차단율 낮음
            "extractor_args": {"youtube": {"player_client": ["tv_embedded", "web_creator", "ios"]}},
        }
        proxy = _get_default_proxy_url()
        if proxy:
            ydl_opts["proxy"] = proxy
        if COOKIES_FILE:
            ydl_opts["cookiefile"] = COOKIES_FILE

        with yt_dlp_module.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not vtt_files:
            raise ValueError("이 영상에서 자막을 찾을 수 없습니다. 자막이 없는 영상일 수 있습니다.")

        def lang_priority(f: str) -> int:
            if ".ko." in f or ".ko-" in f: return 0
            if ".en." in f or ".en-" in f: return 1
            return 2

        vtt_files.sort(key=lang_priority)
        with open(os.path.join(tmpdir, vtt_files[0]), encoding="utf-8") as f:
            content = f.read()

        real_video_id = info.get("id") or video_id
        return _parse_vtt(content), real_video_id


def _fetch_transcript_ytdlp_cli(url: str, video_id: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_tmpl = os.path.join(tmpdir, "%(id)s.%(ext)s")
        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang",
            "ko,en,en-US,ja,zh-Hans",
            "--sub-format",
            "vtt",
            "--skip-download",
            "--no-playlist",
            "--extractor-args",
            "youtube:player_client=tv_embedded,web_creator,ios",
            *(["--cookies", COOKIES_FILE] if COOKIES_FILE else []),
            "-o",
            out_tmpl,
            url,
        ]
        proxy = _get_default_proxy_url()
        if proxy:
            cmd.extend(["--proxy", proxy])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not vtt_files:
            stderr = result.stderr or result.stdout or ""
            if "No video" in stderr or "not a" in stderr.lower():
                raise ValueError("유효하지 않은 YouTube URL입니다.")
            raise ValueError("이 영상에서 자막을 찾을 수 없습니다. 자막이 없는 영상일 수 있습니다.")

        def lang_priority(f: str) -> int:
            if ".ko." in f or ".ko-" in f: return 0
            if ".en." in f or ".en-" in f: return 1
            return 2

        vtt_files.sort(key=lang_priority)
        with open(os.path.join(tmpdir, vtt_files[0]), encoding="utf-8") as f:
            content = f.read()

        return _parse_vtt(content), video_id


def _parse_transcript_list(transcript_list) -> str:
    texts = []
    for item in transcript_list:
        if isinstance(item, dict):
            text = item.get("text", "")
        else:
            text = getattr(item, "text", "")
        text = (text or "").strip()
        if text:
            texts.append(text)
    return " ".join(texts)


def _fetch_transcript_vercel(video_id: str) -> tuple[str, str]:
    """Vercel 서버리스 함수 경유 — Vercel 엣지 IP는 YouTube에 차단되지 않음."""
    worker_url = os.environ.get("YT_WORKER_URL", "").rstrip("/")
    if not worker_url:
        raise ValueError("YT_WORKER_URL 환경변수가 설정되지 않았습니다.")

    resp = requests.get(f"{worker_url}/api/transcript", params={"v": video_id}, timeout=30)
    if resp.status_code == 500:
        raise ValueError(resp.json().get("error", "Vercel 오류"))
    resp.raise_for_status()
    data = resp.json()
    transcript = data.get("transcript", "")
    if not transcript:
        raise ValueError("자막 없음")
    return transcript, video_id


def _fetch_transcript_supadata(video_id: str) -> tuple[str, str]:
    """Supadata API로 자막 가져오기 — 클라우드 IP 차단을 우회하는 전용 서비스."""
    api_key = os.environ.get("SUPADATA_API_KEY")
    if not api_key:
        raise ValueError("SUPADATA_API_KEY 환경변수가 설정되지 않았습니다.")

    resp = requests.get(
        "https://api.supadata.ai/v1/youtube/transcript",
        params={"videoId": video_id, "text": "true"},
        headers={"x-api-key": api_key},
        timeout=30,
    )
    if resp.status_code == 401:
        raise ValueError("Supadata API 키가 유효하지 않습니다.")
    if resp.status_code == 404:
        raise ValueError("이 영상에서 자막을 찾을 수 없습니다.")
    resp.raise_for_status()

    data = resp.json()
    content = data.get("content", "")
    if isinstance(content, list):
        text = " ".join(item.get("text", "") for item in content if item.get("text"))
    else:
        text = str(content)

    if not text:
        raise ValueError("자막 없음")

    return text, video_id


def _fetch_transcript_youtube_api(video_id: str) -> tuple[str, str]:
    """youtube-transcript-api로 자막을 가져옵니다."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            NoTranscriptFound,
            TranscriptsDisabled,
            VideoUnavailable,
        )
    except ModuleNotFoundError:
        raise ValueError("yt_dlp 및 youtube-transcript-api 모두 설치되어 있지 않습니다.")

    try:
        proxies = _build_proxy_dict()
        proxy_config = None
        if proxies:
            from youtube_transcript_api.proxies import GenericProxyConfig
            proxy_config = GenericProxyConfig(
                http_url=proxies.get("http"),
                https_url=proxies.get("https"),
            )

        api = YouTubeTranscriptApi(proxy_config=proxy_config)
        transcript_list = api.fetch(
            video_id,
            languages=["ko", "en", "en-US", "ja", "zh-Hans"],
        )

        return _parse_transcript_list(transcript_list), video_id
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        raise ValueError("이 영상에서 자막을 찾을 수 없습니다. 자막이 없는 영상일 수 있습니다.")
    except Exception as e:
        message = str(e)
        if "blocked" in message.lower() or "ip" in message.lower():
            message = (
                f"{message}. 클라우드 IP 차단일 수 있습니다. "
                "TRANSCRIPT_PROXY/HTTP_PROXY/HTTPS_PROXY 환경변수로 프록시를 지정해보세요."
            )
        raise ValueError(f"자막 요청 실패: {message}")


@app.post("/api/lecture/youtube")
async def fetch_youtube_transcript(req: YouTubeRequest):
    video_id = _extract_video_id(req.url)
    if not video_id:
        return {"error": "유효하지 않은 YouTube URL입니다."}

    loop = asyncio.get_event_loop()
    try:
        # InnerTube 먼저 시도
        transcript = await loop.run_in_executor(
            None, _fetch_transcript_innertube, video_id
        )
        return {"transcript": transcript, "video_id": video_id}
    except Exception:
        pass

    # yt-dlp 폴백
    try:
        transcript, vid = await loop.run_in_executor(
            None, _fetch_transcript_ytdlp, req.url
        )
        return {"transcript": transcript, "video_id": vid}
    except Exception as e2:
        print(f"[yt-dlp 폴백 실패] {e2}", flush=True)

    # 서버 측 모든 방법 실패 — 프론트엔드가 브라우저에서 직접 시도
    return {"error": "server_ip_blocked"}


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


# ── Static Files & SPA ───────────────────────────────────────────────────────

app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("static/index.html")
