# 실험 02: Tool 성공 vs 실패 시 결과 퀄리티 비교

## 실험 설계

동일 작업(밈 번역: `"It's giving main character energy"`)을 3가지 조건으로 실행

| 조건 | 설명 | 예상 결과 |
|------|------|----------|
| MCP 없이 | LLM에게 직접 요청, tool 없음 | 비구조화된 텍스트, JSON 불안정 |
| 잘 만든 MCP | 정확한 description + 구조화된 system prompt | 깔끔한 JSON, 3개 후보 포함 |
| 망가뜨린 MCP | 잘못된 description (문법 교정으로 위장) | 엉뚱한 결과 (번역 대신 문법 교정) |

## 고의 실패 패턴

| 실패 유형 | 적용 tool | 구체적 방법 |
|-----------|----------|------------|
| 타임아웃 | youtube_transcript | 5초 sleep 후 빈 결과 반환 |
| 잘못된 description | meme_translate | "Fix English grammar errors" description으로 에이전트 혼란 |
| 항상 에러 | lecture_analyze | 500 에러 반환 |

## 실행 환경

- 모델: `llama-3.1-8b-instant` (Groq)
- 실행 일시: 2026-05-13
- 입력: `"It's giving main character energy"`
- 1회 실행 결과 (분산 측정 안 함, 발견 중심)

## 결과

| 항목 | MCP 없이 | 잘 만든 MCP | 망가뜨린 MCP |
|------|---------|------------|-------------|
| JSON 유효 여부 | ✅ 유효 | ❌ 무효 (trailing `}` 1개 추가) | ❌ 무효 (JSON 자체 없음) |
| 레이턴시 (초) | 1.14 | 1.32 | 0.34 |
| 토큰 사용량 | 312 | 295 | 97 |
| 번역 품질 (1~5) | 3 | 3 | 0 (번역 자체 거부) |
| 후보 개수 | 4개 (`MC 에너지`, `주인공 에너지`, `MC感`, `주인공감`) | 2개 (`주얼리 에너지`, `주인공 에너지`) — 스키마는 3개 요구 | 0개 |
| 실패 원인 | - | - | description이 "Fix English grammar errors" → 모델이 "교정할 텍스트가 안 보입니다" 응답 |

### 각 조건별 출력 요약

**① MCP 없이** (312 tokens)
```
4개 후보 + 마크다운 + 코드블록 + 설명 + 예시
사람이 읽기엔 좋지만 프로그래밍적으로 파싱 어려움
```

**② 잘 만든 MCP** (295 tokens, JSON 형식 ✓이지만 trailing `}` 1개 추가)
```json
{"original":"...","analysis":{...},"candidates":[2개],"final":{...}}}
                                                                  ↑ extra
```

**③ 망가뜨린 MCP** (97 tokens)
```
However, I don't see a text provided to identify and correct any English
grammar errors. Could you please provide the text you'd like to have corrected?
```

## 분석

### 핵심 발견

1. **JSON 강제는 100% 보장이 아니다.** "JSON만 출력해"라는 강한 system prompt에도 LLM은 trailing brace 1개를 더 붙였다. → MCP tool은 **출력 검증 레이어**를 반드시 가져야 함. 노트북 셀 8의 `parse_tool_calls` 정규식이 그런 안전망의 예시.

2. **description은 행동을 결정한다 — 정확히, 그리고 위험하게.** "문법 교정"이라는 한 줄 description이 입력 텍스트를 "교정 대상이 아님"으로 해석하게 만들었다. 노트북 셀 7에서 본 그대로: **LLM은 코드를 못 보고 description만 본다.**

3. **JSON 무효 = 자유 형식 출력보다 위험할 수 있다.** "잘 만든 MCP"의 JSON-with-extra-brace는 자동 파이프라인에서 무조건 깨진다. 반면 "MCP 없이"의 자유 형식 출력은 사람이 보면 의미를 알 수 있다. **타이트한 스키마는 양날의 검.**

4. **실패 시 응답이 가장 짧다 (97 tokens).** "문법 교정"으로 잘못 라우팅된 모델이 "텍스트가 없습니다"라고 거부 → 빠르게 빈 결과. 에이전트가 후속 재시도/우회를 하지 않으면 작업 통째로 실패.

5. **"잘 만든" 도구도 실제로는 자주 미묘하게 깨진다.** 본 실험에서 가장 흥미로운 결과: 정상이라고 분류한 tool도 결과가 살짝 망가져 있었다. **production 코드에서 출력 검증·재시도가 필수**인 이유.

### 교훈

- **description 정확성** > tool 코드 정확성. (LLM 입장에서 코드는 보이지 않는다)
- **JSON 유효성 검증**을 tool 내부에 넣어야 한다. LLM의 system prompt만 믿으면 안 됨.
- **빈 결과를 반환하는 실패**가 가장 위험. 에이전트가 재시도하지 않으면 무성공 무에러로 통째 실패.
- 짧고 자주 실행되는 작업은 **MCP tool로 분리하는 ROI가 낮을 수 있음**. 출력 검증·재시도 비용이 단순 호출보다 클 때가 있다.

## 추가 실험 아이디어

- 동일 입력으로 5회 반복 → JSON 유효율 분포 보기
- "잘 만든 MCP" 출력에 자동 trailing-brace 정정 후 재실행 → 회복 가능성 확인
- 망가진 MCP의 description을 "한국 신조어 번역" → "맞춤법 교정"으로 점진적으로 바꿔가며 모델이 언제 헷갈리기 시작하는지 임계점 찾기
