---
name: wsl-setup
description: "WSL2 환경 구성 스킬. WSL2 설치 확인, Python/uv 설치, 시스템 패키지 설치, 환경변수 설정. 'WSL2 설정', 'WSL 환경 구성', 'Python 환경 만들어줘', 'uv 설치', '개발 환경 초기화' 요청 시 사용."
---

# WSL2 환경 설정 스킬

WSL2 기반 Hermes Agent 실행 환경을 구성한다.

## 실행 전제

- Windows 10 버전 2004+ 또는 Windows 11
- WSL2가 활성화되어 있어야 함 (미활성 시 PowerShell에서 `wsl --install` 실행)

## 워크플로우

### Step 0: 환경 확인

다음 항목을 순서대로 확인한다:

```bash
# WSL2 여부 확인
uname -r   # 출력에 "microsoft" 포함 여부

# Python 설치 여부
python3 --version 2>/dev/null || echo "NOT INSTALLED"

# uv 설치 여부
uv --version 2>/dev/null || echo "NOT INSTALLED"

# 필수 패키지 확인
which curl git
```

이미 설치된 항목은 건너뛴다.

### Step 1: 시스템 패키지 설치

```bash
sudo apt-get update -y
sudo apt-get install -y \
  curl \
  git \
  build-essential \
  python3-dev \
  libssl-dev
```

### Step 2: uv 설치

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
```

### Step 3: 환경변수 설정

`~/.bashrc` 또는 `~/.zshrc` 에 다음이 없으면 추가:

```bash
export PATH="$HOME/.local/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
```

추가 후 반드시 적용:
```bash
source ~/.bashrc
```

### Step 4: 결과 저장

`_workspace/01_wsl_env_status.md` 파일을 생성하여 다음을 기록:

```markdown
# WSL2 환경 상태

## 확인 항목

- [ ] WSL2 활성 여부: [결과]
- [ ] Python 버전: [결과]
- [ ] uv 버전: [결과]
- [ ] curl/git: [결과]

## PATH 설정

[현재 PATH 값]

## 설치 완료 시각

[ISO 8601 형식]
```

## 알려진 문제와 해결법

| 문제 | 해결법 |
|------|--------|
| `sudo` 비밀번호 요청 | WSL2 사용자 비밀번호 입력 |
| curl 없음 | `sudo apt-get install -y curl` 먼저 실행 |
| PATH 미반영 | 새 터미널 열거나 `source ~/.bashrc` |
| apt lock 오류 | `sudo rm /var/lib/apt/lists/lock` 후 재시도 |
