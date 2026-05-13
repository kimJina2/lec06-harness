"""
MCP Server - lec06_harness 작업 병목 해소 도구 모음

Tools:
  1. youtube_transcript - YouTube 자막 추출
  2. meme_translate     - 해외 밈 → 한국 신조어 초월번역
  3. lecture_analyze    - 강의 자막 → 구조화된 지식베이스
"""

import os
import re
import json
from urllib.parse import urlparse, parse_qs

from mcp.server.fastmcp import FastMCP
from openai import OpenAI

# ── MCP 서버 초기화 ──────────────────────────────────────────────────────────

mcp = FastMCP("lec06-harness-tools")

# ── LLM 클라이언트 설정 ──────────────────────────────────────────────────────

def _get_llm_client() -> tuple[OpenAI, str]:
    """환경변수 기반으로 LLM 클라이언트와 모델명 반환."""
    vllm_url = os.environ.get("VLLM_BASE_URL")
    if vllm_url:
        return OpenAI(base_url=vllm_url, api_key="not-needed"), "qwen-7b"

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key), "llama-3.1-8b-instant"

    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key), "anthropic/claude-haiku-4.5"

    raise RuntimeError("LLM 설정 없음. VLLM_BASE_URL, GROQ_API_KEY, 또는 OPENROUTER_API_KEY 환경변수를 설정하세요.")


# ── Tool 1: YouTube 자막 추출 ────────────────────────────────────────────────

def _extract_video_id(url: str) -> str | None:
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

    if 'youtube.com' in hostname:
        query = parse_qs(parsed.query)
        if query.get('v'):
            return query['v'][0]
        path_segments = [s for s in path.split('/') if s]
        if len(path_segments) >= 2 and path_segments[0] in ('embed', 'shorts'):
            return path_segments[1]

    return None


def _fetch_transcript(video_id: str) -> tuple[str, str]:
    """youtube-transcript-api로 자막 가져오기. 실패 시 InnerTube 폴백."""
    # 1차: youtube-transcript-api
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        transcript_list = api.fetch(video_id, languages=["ko", "en", "en-US", "ja"])
        texts = []
        for item in transcript_list:
            text = (item.text if hasattr(item, 'text') else item.get("text", "")).strip()
            if text:
                texts.append(text)
        return " ".join(texts), "ko"
    except Exception as e1:
        pass

    # 2차: InnerTube API
    import requests
    try:
        session = requests.Session()
        resp = session.get(
            f"https://www.youtube.com/watch?v={video_id}&hl=en",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        match = re.search(r'"captionTracks":\s*\[(.*?)\]', resp.text)
        if not match:
            raise ValueError("자막 트랙을 찾을 수 없습니다")

        captions = json.loads("[" + match.group(1) + "]")
        if not captions:
            raise ValueError("자막이 없습니다")

        # 한국어 > 영어 > 기타 우선
        def lang_priority(cap):
            lang = cap.get("languageCode", "").lower()
            if lang.startswith("ko"): return 0
            if lang.startswith("en"): return 1
            return 2

        captions.sort(key=lang_priority)
        caption_url = captions[0].get("baseUrl")
        detected_lang = captions[0].get("languageCode", "unknown")

        vtt_resp = session.get(caption_url, timeout=10)
        vtt_resp.raise_for_status()

        # VTT 파싱
        texts = []
        for line in vtt_resp.text.split("\n"):
            line = line.strip()
            if not line or line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
                continue
            if "-->" in line or re.match(r"^\d+$", line):
                continue
            text = re.sub(r"<[^>]+>", "", line).strip()
            if text and (not texts or texts[-1] != text):
                texts.append(text)

        return " ".join(texts), detected_lang
    except Exception as e2:
        raise ValueError(f"모든 자막 추출 방법 실패: {e1} / {e2}")


@mcp.tool()
def youtube_transcript(url: str) -> dict:
    """YouTube 영상 URL에서 자막 텍스트를 추출합니다.

    Args:
        url: YouTube 영상 URL (예: https://www.youtube.com/watch?v=dQw4w9WgXcQ)

    Returns:
        자막 텍스트, 비디오 ID, 감지된 언어를 포함한 딕셔너리
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return {"error": "유효하지 않은 YouTube URL입니다."}

    try:
        transcript, language = _fetch_transcript(video_id)
        return {
            "transcript": transcript,
            "video_id": video_id,
            "language": language,
            "char_count": len(transcript),
        }
    except Exception as e:
        return {"error": str(e)}


# ── Tool 2: 밈 번역 ─────────────────────────────────────────────────────────

MEME_SYSTEM_PROMPT = """해외 밈/슬랭을 한국 신조어로 초월번역해. 반드시 아래 JSON만 출력:
{"original":"원문","analysis":{"literal":"직역","real_meaning":"실제의미","tone":"감정톤"},"candidates":[{"text":"후보1","reason":"이유"},{"text":"후보2","reason":"이유"},{"text":"후보3","reason":"이유"}],"final":{"translation":"최종번역","grade":"통과","note":"검수노트"}}"""


@mcp.tool()
def meme_translate(text: str) -> dict:
    """해외 밈이나 슬랭을 한국 최신 신조어로 초월번역합니다.

    3단계 파이프라인: 맥락분석 → 신조어매핑 → 검수

    Args:
        text: 번역할 해외 밈/슬랭 텍스트 (예: "It's giving main character energy")

    Returns:
        원문 분석, 번역 후보 3개, 최종 번역 결과를 포함한 딕셔너리
    """
    client, model = _get_llm_client()

    response = client.chat.completions.create(
        model=model,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": MEME_SYSTEM_PROMPT},
            {"role": "user", "content": f"번역: {text}"},
        ],
    )

    content = response.choices[0].message.content or ""

    # JSON 추출 시도
    try:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    return {"raw_response": content}


# ── Tool 3: 강의 분석 ───────────────────────────────────────────────────────

LECTURE_SYSTEM_PROMPT = """강의 자막을 분석해 한국어로 요약하고 아래 JSON만 출력:
{"title":"제목","language":"언어","summary":"200자요약","sections":[{"index":1,"topic":"주제","content":"내용","key_terms":["용어"],"importance":"HIGH"}],"key_concepts":[{"concept":"개념","definition":"정의","related_to":[],"importance":"HIGH"}],"faq":[{"question":"질문","answer_hint":"힌트","importance":"HIGH"}],"learning_path":["개념1","개념2"]}"""


@mcp.tool()
def lecture_analyze(transcript: str) -> dict:
    """강의 자막을 분석하여 구조화된 지식베이스를 생성합니다.

    섹션 분절, 핵심 개념 추출, FAQ 생성, 학습 경로 제안을 수행합니다.

    Args:
        transcript: 강의 자막 텍스트 (최대 8000자까지 처리)

    Returns:
        제목, 요약, 섹션별 분석, 핵심 개념, FAQ, 학습 경로를 포함한 딕셔너리
    """
    client, model = _get_llm_client()

    # 토큰 제한: 앞 8000자만 처리
    truncated = transcript[:8000]

    response = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": LECTURE_SYSTEM_PROMPT},
            {"role": "user", "content": f"자막:\n{truncated}"},
        ],
    )

    content = response.choices[0].message.content or ""

    try:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["truncated"] = len(transcript) > 8000
            result["original_length"] = len(transcript)
            return result
    except json.JSONDecodeError:
        pass

    return {"raw_response": content, "truncated": len(transcript) > 8000}


# ── 서버 실행 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
