---
name: openrouter-connect
description: "OpenRouter API 연동 스킬. API 키 설정, Hermes config에 provider 연결, 모델 선택, 연결 테스트, 요금 최적화. 'OpenRouter 연결', 'API 키 설정', '모델 바꿔줘', 'OpenRouter 설정', '요금 최적화' 요청 시 사용."
---

# OpenRouter 연동 스킬

Hermes Agent와 OpenRouter API를 연결하고 최적 모델을 설정한다.

## 실행 전제

- Hermes Agent 설치 완료 (`_workspace/02_hermes_setup_status.md` 존재)
- OpenRouter API 키 보유 (openrouter.ai에서 발급)

## 모델 선택 가이드

| 용도 | 모델 ID | 비용 |
|------|---------|------|
| 일반 대화/코딩 (기본 추천) | `anthropic/claude-sonnet-4` | 중간 |
| 빠른 응답 | `anthropic/claude-haiku-4-5` | 낮음 |
| 고성능 추론 | `anthropic/claude-opus-4-6` | 높음 |
| 무료 테스트 | `meta-llama/llama-3.1-8b-instruct:free` | 무료 |
| 한국어 특화 | `google/gemini-pro-1.5` | 중간 |

## 워크플로우

### Step 0: 사전 확인

```bash
# Hermes 설정 상태 확인
cat _workspace/02_hermes_setup_status.md 2>/dev/null || echo "hermes-agent 먼저 실행 필요"

# 기존 API 키 여부 확인
grep -q "OPENROUTER_API_KEY" ~/.hermes/.env 2>/dev/null && echo "KEY EXISTS" || echo "KEY NOT SET"
```

### Step 1: API 키 설정

사용자에게 API 키를 요청하거나, 이미 있으면 사용:

```bash
# ~/.hermes/.env 파일에 저장
echo "OPENROUTER_API_KEY=sk-or-v1-your-key-here" >> ~/.hermes/.env
chmod 600 ~/.hermes/.env   # 파일 권한 보호
```

**주의:** API 키는 코드나 config.yaml에 절대 하드코딩하지 않는다. 반드시 `.env` 파일 사용.

### Step 2: config.yaml provider 설정

`~/.hermes/config.yaml`의 model 섹션을 확인하고 필요 시 수정:

```yaml
model:
  provider: openrouter
  model: anthropic/claude-sonnet-4   # 사용자 선택 또는 기본값
```

### Step 3: 연결 테스트

```bash
# 환경변수 로드
source ~/.hermes/.env

# 간단한 연결 테스트
hermes chat "안녕, 연결 테스트입니다. 한 줄로 응답해주세요."
```

정상 응답이 오면 연결 성공.

### Step 4: 결과 저장

`_workspace/03_openrouter_status.md` 파일 생성:

```markdown
# OpenRouter 연동 상태

## API 설정
- API 키: [설정됨 / 미설정]
- .env 경로: ~/.hermes/.env
- 파일 권한: 600

## 모델 설정
- Provider: openrouter
- 선택 모델: [모델 ID]
- 모델 선택 이유: [이유]

## 연결 테스트
- 테스트 결과: [성공 / 실패]
- 응답 내용: [테스트 응답 일부]

## 완료
Hermes Agent + OpenRouter 연동 완료.
`hermes chat "메시지"` 로 사용 시작 가능.
```

## 알려진 문제와 해결법

| 문제 | 해결법 |
|------|--------|
| `401 Unauthorized` | API 키 오타 확인, openrouter.ai에서 키 재발급 |
| `404 Model not found` | 모델 ID 대소문자 정확히 확인 |
| `429 Rate limit` | 무료 티어 한도 초과, 유료 플랜 전환 또는 모델 변경 |
| `.env` 미로드 | `source ~/.hermes/.env` 수동 실행 |
| 응답 느림 | 더 빠른 모델(`haiku`)로 전환 |
