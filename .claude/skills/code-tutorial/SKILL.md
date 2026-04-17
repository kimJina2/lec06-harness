---
name: code-tutorial
description: "다국어 코드 튜토리얼 자동 생성 오케스트레이터. 해외 개발자 영상의 코드를 추출하여 한국어 주석 코드 파일과 기술 블로그 포스트를 동시 생성. '코드 튜토리얼 만들어줘', '영상 코드 추출', '한국어 주석 달아줘', '블로그 포스트 생성', '코드 설명 블로그', '튜토리얼 다시', '주석 수정' 요청 시 사용."
---

# 다국어 코드 튜토리얼 생성기 오케스트레이터

해외 개발자 영상 코드를 분석하여 한국어 주석 코드 파일 + 기술 블로그 포스트를 동시 생성.
영상 시청 없이도 코드를 즉시 활용할 수 있도록 완전한 한국어 학습 자료를 만든다.

## 실행 모드: 서브 에이전트 (파이프라인 패턴)

Code-Extractor → Comment-Translator → Doc-Generator 순서로 순차 실행.
Comment-Translator의 주석 파일이 Doc-Generator의 블로그 작성 입력이 된다.

## 에이전트 구성

| 에이전트 | subagent_type | 역할 | 입력 | 출력 |
|---------|--------------|------|------|------|
| code-extractor | code-extractor | 영상 코드 추출·재조합 | 자막/텍스트 | `_workspace/01_extracted_code/` |
| comment-translator | comment-translator | 한국어 주석 추가 | `01_extracted_code/` | `_workspace/02_commented_code/` |
| doc-generator | doc-generator | 기술 블로그 포스트 작성 | `02_commented_code/` + metadata | `_workspace/03_blog_post/` |

## 워크플로우

### Phase 0: 컨텍스트 확인

1. `_workspace/` 존재 여부 확인
   - **미존재** → 초기 실행, `_workspace/` 생성 후 Phase 1 진행
   - **존재 + "주석 수정" / "블로그 다시"** → 해당 Phase만 재실행
   - **존재 + 새 입력** → `_workspace/`를 `_workspace_{timestamp}/`로 이동 후 전체 재실행

   **부분 재실행 판단:**
   | 요청 | 재실행 Phase |
   |------|-------------|
   | "주석 스타일 바꿔줘" | Phase 2만 (comment-translator) |
   | "블로그 형식 다르게" | Phase 3만 (doc-generator) |
   | "코드 다시 추출" | Phase 1부터 전체 |
   | "벨로그 형식으로" | Phase 3만 (doc-generator) |

### Phase 1: 코드 추출

```
Agent(
  subagent_type: "code-extractor",
  model: "opus",
  prompt: "다음 입력에서 코드를 추출하라.
           [자막 텍스트 / 코드 스니펫 / URL 삽입]
           결과를 _workspace/01_extracted_code/ 에 저장하라.
           (main.[ext], dependencies.txt, metadata.md)"
)
```

완료 후 `_workspace/01_extracted_code/metadata.md` 존재 확인.
코드가 없다면 사용자에게 알리고 중단.

### Phase 2: 한국어 주석 추가

```
Agent(
  subagent_type: "comment-translator",
  model: "opus",
  prompt: "_workspace/01_extracted_code/ 디렉토리를 읽어라.
           main.[ext]에 한국어 주석을 추가하고,
           _workspace/02_commented_code/ 에 저장하라.
           (main_commented.[ext], comment_summary.md)"
)
```

### Phase 3: 블로그 포스트 생성

```
Agent(
  subagent_type: "doc-generator",
  model: "opus",
  prompt: "다음 파일들을 읽어 기술 블로그 포스트를 작성하라.
           - _workspace/02_commented_code/main_commented.[ext]
           - _workspace/02_commented_code/comment_summary.md
           - _workspace/01_extracted_code/metadata.md
           결과를 _workspace/03_blog_post/ 에 저장하라.
           (post.md, code_final.[ext])"
)
```

### Phase 4: 최종 결과 보고

3개 디렉토리의 결과를 읽어 다음 형식으로 보고:

```
## 튜토리얼 생성 완료

### 생성된 파일
- 📄 주석 코드: _workspace/02_commented_code/main_commented.[ext]
- 📝 블로그 포스트: _workspace/03_blog_post/post.md
- 💾 최종 코드: _workspace/03_blog_post/code_final.[ext]

### 코드 정보
- 언어: [언어]
- 완전성: [완전/불완전]
- 필요 패키지: [목록]

### 블로그 포스트 미리보기
[post.md의 제목 + 첫 섹션]
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| Phase 1 코드 없음 | 개념 설명 중심 블로그로 전환, 사용자에게 알림 |
| 코드 불완전 (`[INCOMPLETE]` 태그) | 해당 부분을 "독자 실습 과제"로 전환하여 계속 진행 |
| Phase 2 언어 불명확 | 가장 가능성 높은 언어로 진행, 불확실 부분 표시 |
| Phase 3 정보 부족 | 가용한 정보로 최선의 포스트 생성, 부족한 섹션은 "추가 설명 필요" 표시 |

## 테스트 시나리오

### 정상 흐름
1. 입력: Python async/await 튜토리얼 영상 자막 텍스트
2. Phase 1: `main.py`, `dependencies.txt`, `metadata.md` 추출
3. Phase 2: `main_commented.py` 생성 (각 라인에 한국어 주석 + Why 설명)
4. Phase 3: `post.md` 생성 (비동기 프로그래밍 개념 → 코드 분석 → 실행 방법)
5. 결과: 영상 없이 즉시 활용 가능한 주석 코드 + 블로그 포스트

### 부분 재실행 흐름
1. 사용자: "블로그를 벨로그 스타일로 다시 써줘"
2. Phase 0: `_workspace/` 존재 + 블로그 재작성 요청 → Phase 3만 재실행
3. doc-generator가 기존 `02_commented_code/` 파일 재활용
4. 새 `post.md` 생성 (벨로그 마크다운 형식)
