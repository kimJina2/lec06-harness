---
name: hermes-env
description: "Hermes Agent + OpenRouter 전체 환경 구축 오케스트레이터. WSL2 설정부터 Hermes 설치, OpenRouter 연동까지 전 과정을 자동화. '환경 구축해줘', '처음부터 설정', 'Hermes 전체 설치', '하네스 실행', '다시 설정', '환경 초기화', '설정 업데이트' 요청 시 사용."
---

# Hermes + OpenRouter 환경 구축 오케스트레이터

WSL2 환경 구성부터 Hermes Agent 설치, OpenRouter API 연동까지 전 과정을 자동화하는 통합 스킬.

## 실행 모드: 서브 에이전트

전문가 풀(Expert Pool) 패턴 — 각 Phase에서 해당 전문 에이전트를 순차 호출.

## 에이전트 구성

| 에이전트 | subagent_type | 역할 | 스킬 | 출력 |
|---------|--------------|------|------|------|
| wsl-env-setup | wsl-env-setup | WSL2/Python 환경 구성 | wsl-setup | `_workspace/01_wsl_env_status.md` |
| hermes-dev | hermes-dev | Hermes Agent 설치/설정 | hermes-agent | `_workspace/02_hermes_setup_status.md` |
| openrouter-mgr | openrouter-mgr | OpenRouter API 연동 | openrouter-connect | `_workspace/03_openrouter_status.md` |

## 워크플로우

### Phase 0: 컨텍스트 확인

`_workspace/` 존재 여부를 확인하여 실행 모드를 결정한다:

1. `_workspace/` 미존재 → **초기 실행**: Phase 1부터 전체 진행
2. `_workspace/` 존재 + 사용자가 특정 Phase 재실행 요청 → **부분 재실행**: 해당 Phase만 실행
3. `_workspace/` 존재 + 처음부터 다시 요청 → **전체 재실행**: 기존 `_workspace/`를 `_workspace_{YYYYMMDD_HHMMSS}/`로 이동 후 Phase 1 진행

**부분 재실행 판단 기준:**
| 사용자 요청 | 실행 Phase |
|------------|-----------|
| "WSL 다시 설정" | Phase 1만 |
| "Hermes 재설치" | Phase 2만 |
| "OpenRouter 키 변경" | Phase 3만 |
| "처음부터", "전체 재실행" | 전체 |

### Phase 1: WSL2 환경 구성

**실행 에이전트:** wsl-env-setup  
**스킬:** `/wsl-setup`

```
Agent(
  subagent_type: "wsl-env-setup",
  model: "opus",
  prompt: "wsl-setup 스킬을 실행하여 WSL2 환경을 구성하라.
           결과를 _workspace/01_wsl_env_status.md에 저장하라.
           작업 디렉토리: [현재 경로]"
)
```

완료 후 `_workspace/01_wsl_env_status.md` 존재 여부 확인. 실패 시 사용자에게 알리고 중단.

### Phase 2: Hermes Agent 설치/설정

**실행 에이전트:** hermes-dev  
**스킬:** `/hermes-agent`  
**전제:** Phase 1 완료

```
Agent(
  subagent_type: "hermes-dev",
  model: "opus",
  prompt: "hermes-agent 스킬을 실행하라.
           _workspace/01_wsl_env_status.md를 먼저 읽고 환경 상태를 파악하라.
           Hermes Agent를 설치하고 config.yaml, SOUL.md를 작성하라.
           결과를 _workspace/02_hermes_setup_status.md에 저장하라."
)
```

완료 후 `_workspace/02_hermes_setup_status.md` 확인. 실패 시 사용자에게 알리고 중단.

### Phase 3: OpenRouter 연동

**실행 에이전트:** openrouter-mgr  
**스킬:** `/openrouter-connect`  
**전제:** Phase 2 완료

```
Agent(
  subagent_type: "openrouter-mgr",
  model: "opus",
  prompt: "openrouter-connect 스킬을 실행하라.
           _workspace/02_hermes_setup_status.md를 먼저 읽어라.
           OpenRouter API 키를 설정하고, 최적 모델을 선택하여 연결 테스트를 실행하라.
           결과를 _workspace/03_openrouter_status.md에 저장하라."
)
```

완료 후 `_workspace/03_openrouter_status.md` 확인.

### Phase 4: 최종 보고

3개의 결과 파일을 읽어 사용자에게 요약 보고:

```markdown
## Hermes + OpenRouter 환경 구축 완료

### 구축 결과
- Phase 1 (WSL2): [성공/실패]
- Phase 2 (Hermes): [성공/실패]  
- Phase 3 (OpenRouter): [성공/실패]

### 사용 시작
hermes chat "안녕하세요"

### 설정 파일 위치
- Hermes config: ~/.hermes/config.yaml
- API 키: ~/.hermes/.env
- SOUL.md: ~/.hermes/SOUL.md
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| Phase 1 실패 | WSL2 미설치 안내, 사용자에게 Windows PowerShell에서 `wsl --install` 실행 요청 후 중단 |
| Phase 2 실패 | 설치 로그 확인, 1회 재시도. 재실패 시 에러 내용 사용자에게 보고 |
| Phase 3 실패 | API 키 오류인 경우 사용자에게 키 재확인 요청. 연결 실패는 Phase 3만 재실행 안내 |
| 전체 실패 | `_workspace/` 보존, 각 Phase 결과 파일로 실패 지점 식별 가능 |

## 테스트 시나리오

### 정상 흐름
1. 사용자: "Hermes 환경 전체 설정해줘"
2. Phase 0: `_workspace/` 없음 → 초기 실행 결정
3. Phase 1: wsl-env-setup 실행 → `01_wsl_env_status.md` 생성
4. Phase 2: hermes-dev 실행 → `02_hermes_setup_status.md` 생성
5. Phase 3: openrouter-mgr 실행 → `03_openrouter_status.md` 생성
6. Phase 4: 3개 파일 통합 → 최종 보고
7. 예상 결과: `hermes chat` 명령으로 즉시 사용 가능

### 에러 흐름 (Phase 3 실패)
1. Phase 1, 2 성공
2. Phase 3에서 API 키 오류로 실패
3. 사용자에게 OpenRouter 대시보드에서 키 확인 요청
4. 사용자가 올바른 키 제공 후 "OpenRouter 키 다시 설정해줘" 요청
5. Phase 0에서 `_workspace/` 존재 확인 → Phase 3만 재실행
6. 연결 성공 후 최종 보고
