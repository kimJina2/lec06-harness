---
name: hermes-agent
description: "Hermes Agent 설치/설정 스킬. Hermes 설치, config.yaml 작성, SOUL.md 설계, 커스텀 스킬 등록, 기억 시스템 설정. 'Hermes 설치', 'Hermes 설정', 'SOUL.md 만들어줘', 'Hermes 스킬 추가', 'Hermes 실행' 요청 시 사용."
---

# Hermes Agent 설치/설정 스킬

NousResearch의 Hermes Agent를 WSL2 환경에 설치하고 설정한다.

## 실행 전제

- WSL2 환경 구성 완료 (`_workspace/01_wsl_env_status.md` 존재)
- curl 설치됨

## 워크플로우

### Step 0: 사전 확인

```bash
# Hermes 이미 설치됐는지 확인
hermes --version 2>/dev/null || echo "NOT INSTALLED"

# WSL2 환경 상태 확인
cat _workspace/01_wsl_env_status.md 2>/dev/null || echo "wsl-setup 먼저 실행 필요"
```

### Step 1: Hermes Agent 설치

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
hermes --version
```

### Step 2: 설정 디렉토리 확인

```bash
ls ~/.hermes/
# 없으면 생성
mkdir -p ~/.hermes
```

### Step 3: config.yaml 작성

`~/.hermes/config.yaml` 작성 (provider는 openrouter-mgr 스킬이 이어서 설정):

```yaml
model:
  provider: openrouter
  model: anthropic/claude-sonnet-4

memory:
  enabled: true
  ftss: true

interface:
  messaging:
    - telegram   # 필요 시 활성화
  tts: false     # TTS 필요 시 true

skills:
  auto_generate: true
  directory: ~/.hermes/skills/
```

### Step 4: SOUL.md 작성

사용자가 원하는 에이전트 정체성이 없으면 기본 템플릿 사용:

`~/.hermes/SOUL.md`:

```markdown
# Hermes의 SOUL

## 정체성
나는 자기 학습형 AI 어시스턴트다. 사용자의 작업을 완료한 후 스킬을 자동 생성하여
재사용할수록 더 빠르고 정확하게 작업한다.

## 핵심 가치
- **정확성**: 불확실한 정보는 추측하지 않고 명시한다
- **효율성**: 이전 경험(스킬)을 최대한 활용한다
- **투명성**: 수행하는 작업과 그 이유를 명확히 설명한다

## 행동 원칙
- 작업 완료 후 반드시 스킬로 저장한다
- 기억 시스템을 활용하여 세션 간 맥락을 유지한다
- 사용자 요청의 의도를 파악하고 가장 적합한 방법을 선택한다

## 금지 행동
- 확인되지 않은 정보를 사실처럼 제시하지 않는다
- 사용자 동의 없이 파일을 삭제하지 않는다
```

### Step 5: 결과 저장

`_workspace/02_hermes_setup_status.md` 파일 생성:

```markdown
# Hermes Agent 설정 상태

## 설치 결과
- Hermes 버전: [결과]
- 설치 경로: [결과]

## 설정 파일
- config.yaml: [경로]
- SOUL.md: [경로]

## 메모리 시스템
- FTSS 활성: [true/false]

## 다음 단계
openrouter-connect 스킬로 API 연결 완료 필요
```

## 알려진 문제와 해결법

| 문제 | 해결법 |
|------|--------|
| 설치 스크립트 실패 | `curl -v` 로 네트워크 확인, GitHub 접근 가능 여부 확인 |
| `hermes` 명령 없음 | `source ~/.bashrc` 후 재시도, PATH 확인 |
| config.yaml YAML 오류 | 탭 대신 스페이스 2칸, 들여쓰기 일관성 확인 |
| 메모리 디렉토리 오류 | `mkdir -p ~/.hermes/memory` 수동 생성 |
