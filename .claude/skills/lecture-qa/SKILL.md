---
name: lecture-qa
description: "실시간 강의·세미나 인터랙티브 번역 오케스트레이터. 해외 대학 강의나 기술 세미나 자막을 분석하여 사용자가 질문하면 영상 내용에 기반해 답변하는 러닝 파트너. '강의 분석', '세미나 Q&A', '강의 질문', '영상 내용 물어보기' 요청 시 사용."
---

# 실시간 강의/세미나 인터랙티브 Q&A 오케스트레이터

해외 강의·세미나 자막을 분석하여 사용자가 영상 내용과 대화할 수 있는 러닝 파트너 하네스.
단순 시청을 넘어 강의 내용을 질문하고, 개념을 검증하고, 심화 학습할 수 있도록 지원한다.

## 실행 모드: 서브 에이전트 (파이프라인 패턴)

Transcription-Agent → Knowledge-Graph-Builder → Q&A-Agent 순서로 실행.
Phase 1~2는 자막 로딩 시 1회 실행, Phase 3은 질문마다 반복 실행.

## 에이전트 구성

| 에이전트 | subagent_type | 역할 | 입력 | 출력 |
|---------|--------------|------|------|------|
| transcription-agent | transcription-agent | 자막 구조화·섹션 분절 | 원시 자막 텍스트 | 구조화된 섹션 JSON |
| knowledge-graph-builder | knowledge-graph-builder | 개념 관계망·FAQ 구축 | 섹션 JSON | 지식 베이스 JSON |
| qa-agent | qa-agent | 질문 응답 | 지식 베이스 + 질문 | 답변 텍스트 |

## 워크플로우

### Phase 0: 컨텍스트 확인

- `_workspace/lecture/` 존재 여부 확인
- 기존 강의 로드 vs 새 강의 입력 판단

### Phase 1: 자막 구조화 (강의 로딩 시 1회)

```
Agent(
  subagent_type: "transcription-agent",
  model: "opus",
  prompt: "다음 자막 텍스트를 구조화하라.
           [자막 텍스트]
           결과를 _workspace/lecture/01_structured.json 에 저장하라."
)
```

### Phase 2: 지식 베이스 구축 (강의 로딩 시 1회)

```
Agent(
  subagent_type: "knowledge-graph-builder",
  model: "opus",
  prompt: "_workspace/lecture/01_structured.json을 읽어 지식 베이스를 구축하라.
           결과를 _workspace/lecture/02_knowledge.json 에 저장하라."
)
```

### Phase 3: Q&A (질문마다 반복)

```
Agent(
  subagent_type: "qa-agent",
  model: "opus",
  prompt: "지식 베이스: [02_knowledge.json 내용]
           대화 히스토리: [이전 대화]
           질문: [사용자 질문]
           강의 내용에 기반해 답변하라."
)
```

### Phase 4: 결과 보고

답변을 사용자에게 전달하고 후속 질문을 유도한다.

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| 자막 없음 | 코드/텍스트만으로 지식 베이스 구축 |
| 강의 범위 초과 질문 | "강의 외 내용" 명시 후 일반 지식으로 보충 |
| 질문 불명확 | 명확화 질문으로 되묻기 |
