# Hermes Agent + OpenRouter 개발 환경 하네스

## 하네스 포인터

이 프로젝트는 WSL2 환경에서 Hermes Agent와 OpenRouter를 연결하는 개발 환경을 자동화하는 하네스입니다.

### 스킬 트리거 규칙

- **전체 환경 구축/설정 시작**: `/hermes-env` 스킬 (오케스트레이터)
- **WSL2 환경만 설정**: `/wsl-setup` 스킬
- **Hermes Agent 설치/설정**: `/hermes-agent` 스킬
- **OpenRouter 연결/모델 관리**: `/openrouter-connect` 스킬

### 에이전트 팀

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| wsl-env-setup | `.claude/agents/wsl-env-setup.md` | WSL2 환경 구성, Python/uv, 시스템 의존성 |
| hermes-dev | `.claude/agents/hermes-dev.md` | Hermes Agent 설치/설정, SOUL.md, 스킬 개발 |
| openrouter-mgr | `.claude/agents/openrouter-mgr.md` | OpenRouter API 연동, 모델 선택, 요금 최적화 |

### 아키텍처

- **패턴**: 전문가 풀 (Expert Pool)
- **실행 모드**: 서브 에이전트
- **워크플로우**: Phase 0(환경 확인) → Phase 1(WSL2) → Phase 2(Hermes) → Phase 3(OpenRouter)

---

## 하네스 2: 글로벌 밈 문화 번역기

해외 밈·슬랭을 한국 최신 신조어로 초월 번역하는 엔터테인먼트 자막 전용 하네스.

### 스킬 트리거 규칙

- **밈/슬랭 번역 전체**: `/meme-translate` 스킬 (오케스트레이터)

### 에이전트 팀

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| slang-decoder | `.claude/agents/slang-decoder.md` | 해외 밈·슬랭 맥락·뉘앙스 분석 |
| trend-monitor | `.claude/agents/trend-monitor.md` | 한국 최신 신조어 매핑, 후보 제시 |
| sensitivity-checker | `.claude/agents/sensitivity-checker.md` | 표현 적절성 검수, 플랫폼별 사용 가능 여부 |

### 아키텍처

- **패턴**: 파이프라인 (Slang-Decoder → Trend-Monitor → Sensitivity-Checker)
- **실행 모드**: 서브 에이전트
- **핵심 가치**: 재미 — 정확한 번역보다 공감되는 초월 번역

---

## 하네스 3: 실시간 강의/세미나 인터랙티브 번역

해외 대학 강의·기술 세미나 자막을 분석하여 사용자가 강의 내용과 대화할 수 있는 러닝 파트너 하네스.

### 스킬 트리거 규칙

- **강의 Q&A 전체**: `/lecture-qa` 스킬 (오케스트레이터)

### 에이전트 팀

| 에이전트 | 파일 | 역할 |
|---------|------|------|
| transcription-agent | `.claude/agents/transcription-agent.md` | 자막 구조화·섹션 분절 |
| knowledge-graph-builder | `.claude/agents/knowledge-graph-builder.md` | 개념 관계망·FAQ 지식 베이스 구축 |
| qa-agent | `.claude/agents/qa-agent.md` | 강의 기반 질의응답 |

### 아키텍처

- **패턴**: 파이프라인 (Transcription → Knowledge-Graph → Q&A)
- **실행 모드**: 서브 에이전트
- **핵심 가치**: 단순 시청을 넘어 강의 내용과 대화하는 러닝 파트너

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|---------|
| 2026-04-12 | 초기 하네스 구축 (Hermes + OpenRouter) |
| 2026-04-12 | 밈 번역기, 코드 튜토리얼 생성기 하네스 추가 |
| 2026-04-12 | 코드 튜토리얼 → 실시간 강의 인터랙티브 번역 하네스로 교체 |
