"""
MCP Server (의도적 실패 버전) - 실험 02용

고의로 주입한 실패 패턴:
  1. youtube_transcript - 5초 타임아웃 후 빈 결과 반환
  2. meme_translate     - 잘못된 description으로 에이전트 혼란 유발
  3. lecture_analyze    - 항상 에러 반환
"""

import os
import re
import json
import time

from mcp.server.fastmcp import FastMCP
from openai import OpenAI

mcp = FastMCP("lec06-harness-tools-broken")


def _get_llm_client() -> tuple[OpenAI, str]:
    vllm_url = os.environ.get("VLLM_BASE_URL")
    if vllm_url:
        return OpenAI(base_url=vllm_url, api_key="not-needed"), "qwen-7b"
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        return OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key), "llama-3.1-8b-instant"
    raise RuntimeError("LLM 설정 없음")


# ── 실패 패턴 1: 타임아웃 + 빈 결과 ─────────────────────────────────────────

@mcp.tool()
def youtube_transcript(url: str) -> dict:
    """YouTube 영상 URL에서 자막 텍스트를 추출합니다."""
    # 의도적 실패: 5초 지연 후 빈 결과
    time.sleep(5)
    return {"transcript": "", "video_id": "", "language": ""}


# ── 실패 패턴 2: 잘못된 description ──────────────────────────────────────────

@mcp.tool()
def meme_translate(text: str) -> dict:
    """주어진 텍스트의 영어 문법을 교정합니다. 맞춤법과 문법 오류를 찾아 수정합니다."""
    # description이 '문법 교정'이라고 되어 있어서 에이전트가 잘못된 상황에서 호출함
    # 실제로는 번역을 시도하지만, 프롬프트가 엉뚱함
    client, model = _get_llm_client()
    response = client.chat.completions.create(
        model=model,
        max_tokens=256,
        messages=[
            {"role": "system", "content": "Fix English grammar errors in the text."},
            {"role": "user", "content": text},
        ],
    )
    return {"result": response.choices[0].message.content or ""}


# ── 실패 패턴 3: 항상 에러 ───────────────────────────────────────────────────

@mcp.tool()
def lecture_analyze(transcript: str) -> dict:
    """강의 자막을 분석하여 구조화된 지식베이스를 생성합니다."""
    # 의도적 실패: 항상 에러 반환
    return {"error": "Internal server error: model not loaded", "code": 500}


if __name__ == "__main__":
    mcp.run()
