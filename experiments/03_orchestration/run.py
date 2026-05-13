"""
실험 03: Orchestration 3패턴 비교 실험

동일 작업(밈 번역 + 강의 분석)을 3가지 패턴으로 실행:
  ① 싱글 에이전트 (모든 작업을 하나가 순차 처리)
  ② Planner + Executor (계획 수립 → 실행 분리)
  ③ 병렬 sub-agent (작업별 독립 에이전트)

측정 항목: 토큰 사용량, 레이턴시, 실패 발생 레이어

실행: python run.py
"""

import os
import sys
import json
import time
import concurrent.futures
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
    print("VLLM_BASE_URL 또는 GROQ_API_KEY를 설정하세요.")
    sys.exit(1)

# ── 테스트 입력 ──────────────────────────────────────────────────────────────

TEST_MEME = "It's giving main character energy"
TEST_TRANSCRIPT = """Today we're going to talk about transformer architecture.
The key innovation is the self-attention mechanism, which allows the model
to look at all positions in the input sequence simultaneously.
Unlike RNNs, transformers don't process tokens sequentially.
The attention formula is Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) V.
This enables parallelization during training, making transformers much faster.
Multi-head attention allows the model to attend to information from different
representation subspaces. We use 8 heads in the base model."""

MEME_SYSTEM = """해외 밈/슬랭을 한국 신조어로 초월번역해. 반드시 아래 JSON만 출력:
{"original":"원문","analysis":{"literal":"직역","real_meaning":"실제의미","tone":"감정톤"},"candidates":[{"text":"후보1","reason":"이유"},{"text":"후보2","reason":"이유"},{"text":"후보3","reason":"이유"}],"final":{"translation":"최종번역","grade":"통과","note":"검수노트"}}"""

LECTURE_SYSTEM = """강의 자막을 분석해 한국어로 요약하고 아래 JSON만 출력:
{"title":"제목","summary":"200자요약","sections":[{"index":1,"topic":"주제","content":"내용","key_terms":["용어"],"importance":"HIGH"}],"key_concepts":[{"concept":"개념","definition":"정의","importance":"HIGH"}],"faq":[{"question":"질문","answer_hint":"힌트"}]}"""


def _call_llm(system: str, user_msg: str, max_tokens: int = 1024) -> tuple[str, int]:
    """LLM 호출 후 (응답텍스트, 토큰수) 반환."""
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
    )
    content = resp.choices[0].message.content or ""
    tokens = resp.usage.total_tokens if resp.usage else 0
    return content, tokens


# ── 패턴 ① 싱글 에이전트 ────────────────────────────────────────────────────

def pattern_single():
    """모든 작업을 하나의 에이전트가 순차 처리."""
    print("\n" + "=" * 60)
    print("패턴 ①: 싱글 에이전트 (순차 처리)")
    print("=" * 60)

    start = time.time()
    total_tokens = 0

    # 작업 1: 밈 번역
    meme_result, t1 = _call_llm(MEME_SYSTEM, f"번역: {TEST_MEME}")
    total_tokens += t1

    # 작업 2: 강의 분석
    lecture_result, t2 = _call_llm(LECTURE_SYSTEM, f"자막:\n{TEST_TRANSCRIPT}")
    total_tokens += t2

    elapsed = time.time() - start

    result = {
        "pattern": "single",
        "latency_sec": round(elapsed, 2),
        "total_tokens": total_tokens,
        "meme_output": meme_result[:200],
        "lecture_output": lecture_result[:200],
        "failure_layer": None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ── 패턴 ② Planner + Executor ───────────────────────────────────────────────

def pattern_planner_executor():
    """Planner가 계획 수립 → Executor가 실행."""
    print("\n" + "=" * 60)
    print("패턴 ②: Planner + Executor")
    print("=" * 60)

    start = time.time()
    total_tokens = 0

    # Phase 1: Planner - 작업 분해
    planner_prompt = f"""다음 두 작업을 수행해야 합니다. 실행 계획을 JSON으로 작성하세요:
1. 밈 번역: "{TEST_MEME}"
2. 강의 분석: (자막 제공됨)

출력 형식: {{"steps": [{{"id": 1, "task": "...", "tool": "...", "input": "..."}}]}}"""

    plan, t_plan = _call_llm(
        "당신은 작업 계획을 수립하는 Planner입니다. JSON으로만 응답하세요.",
        planner_prompt,
        max_tokens=512,
    )
    total_tokens += t_plan

    # Phase 2: Executor - 계획에 따라 순차 실행
    meme_result, t1 = _call_llm(MEME_SYSTEM, f"번역: {TEST_MEME}")
    total_tokens += t1

    lecture_result, t2 = _call_llm(LECTURE_SYSTEM, f"자막:\n{TEST_TRANSCRIPT}")
    total_tokens += t2

    elapsed = time.time() - start

    result = {
        "pattern": "planner_executor",
        "latency_sec": round(elapsed, 2),
        "total_tokens": total_tokens,
        "plan": plan[:200],
        "meme_output": meme_result[:200],
        "lecture_output": lecture_result[:200],
        "failure_layer": None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ── 패턴 ③ 병렬 sub-agent ───────────────────────────────────────────────────

def pattern_parallel_subagent():
    """독립 작업을 병렬 sub-agent로 동시 실행."""
    print("\n" + "=" * 60)
    print("패턴 ③: 병렬 sub-agent")
    print("=" * 60)

    start = time.time()
    total_tokens = 0

    def meme_agent():
        return _call_llm(MEME_SYSTEM, f"번역: {TEST_MEME}")

    def lecture_agent():
        return _call_llm(LECTURE_SYSTEM, f"자막:\n{TEST_TRANSCRIPT}")

    # 병렬 실행
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_meme = executor.submit(meme_agent)
        future_lecture = executor.submit(lecture_agent)

        meme_result, t1 = future_meme.result()
        lecture_result, t2 = future_lecture.result()

    total_tokens += t1 + t2
    elapsed = time.time() - start

    result = {
        "pattern": "parallel_subagent",
        "latency_sec": round(elapsed, 2),
        "total_tokens": total_tokens,
        "meme_output": meme_result[:200],
        "lecture_output": lecture_result[:200],
        "failure_layer": None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


# ── 결과 비교 ────────────────────────────────────────────────────────────────

def print_benchmark(results: list[dict]):
    print("\n" + "=" * 60)
    print("벤치마크 결과표")
    print("=" * 60)
    print(f"{'패턴':<25} {'레이턴시(초)':<15} {'토큰':<12} {'실패 레이어':<15}")
    print("-" * 67)
    for r in results:
        print(f"{r['pattern']:<25} {r['latency_sec']:<15} {r['total_tokens']:<12} {r['failure_layer'] or '-':<15}")

    # 속도 비교
    if len(results) >= 3:
        single = results[0]["latency_sec"]
        parallel = results[2]["latency_sec"]
        if single > 0:
            speedup = round(single / parallel, 2) if parallel > 0 else 0
            print(f"\n병렬 대비 싱글 속도비: {speedup}x")


# ── 실행 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = []
    results.append(pattern_single())
    results.append(pattern_planner_executor())
    results.append(pattern_parallel_subagent())
    print_benchmark(results)

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n결과가 results.json에 저장되었습니다.")
