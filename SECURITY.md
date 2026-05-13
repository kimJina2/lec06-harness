# 보안 가이드 (Security)

> 본 저장소는 public입니다. 시크릿 누출이 곧 금전적·계정 피해로 이어지니
> 이 문서의 규칙을 반드시 지켜 주세요.

## 1. 절대로 커밋하면 안 되는 것

- API 키 (`OPENROUTER_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, …)
- GitHub Personal Access Token (`ghp_…`, `github_pat_…`)
- 서비스 계정 JSON (Google/GCP/Firebase)
- AWS / Azure / Vercel / Render 인증 정보
- 개인 식별 정보 (이메일·전화번호 등)
- DB 접속 문자열에 password가 포함된 경우

## 2. 시크릿 보관 원칙

### 로컬 개발
- 항상 `.env` 파일에만 (이미 `.gitignore` 처리됨)
- 예시는 `.env.example`에 placeholder만 — 실제 값 금지
- 사용 예:
  ```bash
  cp app/.env.example app/.env
  # .env 안의 REPLACE_ME를 실제 값으로
  ```

### 배포 환경
| 플랫폼 | 시크릿 저장 위치 |
|--------|----------------|
| Render | Dashboard → Service → Environment → Add Variable |
| Vercel | Dashboard → Project → Settings → Environment Variables |
| GitHub Actions | Repo → Settings → Secrets and variables → Actions |

코드 안에서는 `process.env.X` / `os.environ['X']`로만 접근.

## 3. Git remote URL에 토큰 박지 말 것

❌ **잘못된 예 (이전에 이 저장소가 빠졌던 함정):**
```
url = https://USERNAME:ghp_AAAA@github.com/...
```
`.git/config` 평문에 그대로 남아 누구든 컴퓨터 접근 시 노출.

✅ **올바른 방법:**
```bash
# URL에는 토큰 없이
git remote set-url origin https://github.com/OWNER/REPO.git

# 인증은 credential helper에 위임
# 옵션 A) GitHub CLI (가장 안전)
gh auth login

# 옵션 B) git credential store (~/.git-credentials에만 저장)
git config --global credential.helper store
# 다음 push 때 한 번 입력 → 이후 자동
```

## 4. 시크릿이 이미 노출됐다면 (사후 조치 체크리스트)

### A. 즉시 (5분 이내)
1. [ ] 노출된 키를 **revoke** — 발급처에서 즉시 삭제
   - GitHub PAT: https://github.com/settings/tokens
   - OpenRouter: https://openrouter.ai/keys
   - Groq: https://console.groq.com/keys
   - OpenAI: https://platform.openai.com/api-keys
2. [ ] 새 키 발급

### B. 30분 이내
3. [ ] 모든 배포 환경에 새 키 반영 (Render, Vercel, …)
4. [ ] 로컬 `.env` 갱신
5. [ ] 사용량 청구 페이지에서 비정상 호출 확인

### C. 1시간 이내
6. [ ] git history 검사:
   ```bash
   git log --all -p | grep -E "(ghp_|sk-|gsk_)" | head
   ```
7. [ ] 만약 커밋에 박혀 있다면 `git filter-repo` 또는 `bfg-repo-cleaner`로 제거.
   force push 필요 (협업자 있으면 사전 공지)

## 5. 사전 차단 도구 (권장 설치)

### A. pre-commit 훅 — 커밋 전 시크릿 자동 차단
```bash
pip install pre-commit detect-secrets
cat > .pre-commit-config.yaml <<'EOF'
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
EOF
pre-commit install
detect-secrets scan > .secrets.baseline
```

### B. gitleaks (CI/CD에서 검사)
```yaml
# .github/workflows/security.yml
- uses: gitleaks/gitleaks-action@v2
```

## 6. 이 저장소의 현재 보호 수준

- [x] `.gitignore`: `.env`, `*.pem`, `*.key`, `*-secret.*`, service-account JSON 등 광범위 차단
- [x] `app/.env.example`: placeholder만 포함
- [x] `render.yaml`: `sync: false`로 실제 값은 Render 대시보드에서만 관리
- [x] git history: 시크릿 0건 확인 완료 (2026-05-13 기준)
- [ ] pre-commit 훅 — 추가 권장 (현재 미설치)
- [ ] CI 시크릿 스캔 — 추가 권장

## 7. 이 저장소 사용 시 체크리스트 (Contributor)

```
[ ] .env.example을 .env로 복사 후 본인 키 입력
[ ] git status로 .env가 untracked인지 확인
[ ] 푸시 전 git diff | grep -E "(sk-|ghp_|gsk_)" 한 번 더
[ ] 절대로 README나 코드 주석에 실제 키 예시 박지 않기
```
