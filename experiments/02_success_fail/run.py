"""
실험 02: Tool 성공 vs 실패 시 결과 퀄리티 비교

동일 작업을 3가지 조건으로 실행:
  ① MCP 없이 (LLM 단독)
  ② 잘 만든 MCP (server.py)
  ③ 망가뜨린 MCP (server_broken.py)

실행: python run.py
"""

import os
import sys
import json
import time
from openai import OpenAI

# ── 설정 ─────────────────────────────────────────────────────────────────────

VLLM_URL = os.environ.get("VLLM_BASE_URL", "")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")

if VLLM_URL:
    client = OpenAI(base_url=VLLM_URL, api_key="not-needed")
    MODEL = "qwen-7b"
elif GROQ_KEY:
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_KEY)
    MODEL = "llama-3.1-8b-instant"
else:
    print("VLLM_BASE_URL 또는 GROQ_API_KEY 환경변수를 설정하세요.")
    sys.exit(1)

# ── 테스트 케이스 ────────────────────────────────────────────────────────────

TEST_MEME = "It's giving main character energy"
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# ── 조건 ① MCP 없이 (LLM 단독) ──────────────────────────────────────────────

def run_without_mcp():
    """MCP tool 없이 LLM에게 직접 요청."""
    print("\n" + "=" * 60)
    print("조건 ①: MCP 없이 (LLM 단독)")
    print("=" * 60)

    start = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {"role": "user", "content": f"해외 밈 '{TEST_MEME}'을 한국 신조어로 번역해줘. JSON으로 응답해."},
        ],
    )
    elapsed = time.time() - start
    content = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0

    result = {
        "condition": "no_mcp",
        "task": "meme_translate",
        "input": TEST_MEME,
        "output": content[:500],
        "latency_sec": round(elapsed, 2),
        "tokens": tokens,
        "has_structured_json": _is_valid_json(content),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ── 조건 ② 잘 만든 MCP ──────────────────────────────────────────────────────

def run_with_good_mcp():
    """정상 MCP tool을 사용한 요청 시뮬레이션."""
    print("\n" + "=" * 60)
    print("조건 ②: 잘 만든 MCP (정상 tool)")
    print("=" * 60)

    # MCP tool의 동작을 시뮬레이션 (실제로는 server.py의 meme_translate와 동일)
    start = time.time()

    # tool 호출: 구조화된 system prompt로 번역
    system = """해외 밈/슬랭을 한국 신조어로 초월번역해. 반드시 아래 JSON만 출력:
{"original":"원문","analysis":{"literal":"직역","real_meaning":"실제의미","tone":"감정톤"},"candidates":[{"text":"후보1","reason":"이유"},{"text":"후보2","reason":"이유"},{"text":"후보3","reason":"이유"}],"final":{"translation":"최종번역","grade":"통과","note":"검수노트"}}"""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"번역: {TEST_MEME}"},
        ],
    )
    elapsed = time.time() - start
    content = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0

    result = {
        "condition": "good_mcp",
        "task": "meme_translate",
        "input": TEST_MEME,
        "output": content[:500],
        "latency_sec": round(elapsed, 2),
        "tokens": tokens,
        "has_structured_json": _is_valid_json(content),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ── 조건 ③ 망가뜨린 MCP ─────────────────────────────────────────────────────

def run_with_broken_mcp():
    """망가뜨린 MCP tool 시뮬레이션 (잘못된 description)."""
    print("\n" + "=" * 60)
    print("조건 ③: 망가뜨린 MCP (잘못된 description)")
    print("=" * 60)

    start = time.time()

    # 의도적 실패: description이 '문법 교정'으로 되어 있어 엉뚱한 프롬프트 사용
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=256,
        messages=[
            {"role": "system", "content": "Fix English grammar errors in the text."},
            {"role": "user", "content": TEST_MEME},
        ],
    )
    elapsed = time.time() - start
    content = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0

    result = {
        "condition": "broken_mcp",
        "task": "meme_translate",
        "input": TEST_MEME,
        "output": content[:500],
        "latency_sec": round(elapsed, 2),
        "tokens": tokens,
        "has_structured_json": _is_valid_json(content),
        "failure_type": "wrong_description",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def _is_valid_json(text: str) -> bool:
    import re
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        return False
    try:
        json.loads(match.group())
        return True
    except json.JSONDecodeError:
        return False


def print_comparison(results: list[dict]):
    print("\n" + "=" * 60)
    print("비교 결과표")
    print("=" * 60)
    print(f"{'조건':<20} {'JSON 유효':<12} {'레이턴시':<12} {'토큰':<10}")
    print("-" * 54)
    for r in results:
        print(f"{r['condition']:<20} {str(r['has_structured_json']):<12} {r['latency_sec']:<12} {r['tokens']:<10}")


# ── 실행 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = []
    results.append(run_without_mcp())
    results.append(run_with_good_mcp())
    results.append(run_with_broken_mcp())
    print_comparison(results)

    # 결과 저장
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n결과가 results.json에 저장되었습니다.")
