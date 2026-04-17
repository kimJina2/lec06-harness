---
name: meme-translate
description: "글로벌 밈/슬랭 문화 번역 오케스트레이터. 해외 밈·인터넷 슬랭·유행어를 한국 최신 신조어로 초월 번역. '밈 번역', '슬랭 번역해줘', '이 표현 한국어로', '자막 초월번역', '해외 유행어 뭔 뜻이야', '번역 다시', '다른 표현으로' 요청 시 사용."
---

# 밈 문화 번역기 오케스트레이터

해외 밈·슬랭을 한국 최신 유행어로 치환하는 초월 번역 파이프라인.
재미와 문화적 공감이 핵심이며, 직역 대신 감정 톤이 동일한 한국 표현으로 치환한다.

## 실행 모드: 서브 에이전트 (파이프라인 패턴)

Slang-Decoder → Trend-Monitor → Sensitivity-Checker 순서로 순차 실행.
각 에이전트의 출력이 다음 에이전트의 입력이 되는 파이프라인 구조.

## 에이전트 구성

| 에이전트 | subagent_type | 역할 | 입력 | 출력 |
|---------|--------------|------|------|------|
| slang-decoder | slang-decoder | 해외 밈 맥락·뉘앙스 분석 | 원문 | `_workspace/01_slang_analysis.md` |
| trend-monitor | trend-monitor | 한국 신조어 매핑 | `01_slang_analysis.md` | `_workspace/02_korean_mapping.md` |
| sensitivity-checker | sensitivity-checker | 표현 적절성 검수 | `02_korean_mapping.md` | `_workspace/03_final_translation.md` |

## 워크플로우

### Phase 0: 컨텍스트 확인

1. `_workspace/` 존재 여부 확인
   - **미존재** → 초기 실행, `_workspace/` 생성 후 Phase 1 진행
   - **존재 + "다른 표현으로" / "다시 번역"** → sensitivity-checker만 재실행 (02 결과 재활용)
   - **존재 + 새 원문 입력** → 전체 재실행 (`_workspace/`를 `_workspace_{timestamp}/`로 이동)

### Phase 1: 해외 슬랭 분석

```
Agent(
  subagent_type: "slang-decoder",
  model: "opus",
  prompt: "다음 해외 밈/슬랭을 분석하라.
           [원문 텍스트 삽입]
           분석 결과를 _workspace/01_slang_analysis.md에 저장하라."
)
```

완료 후 `_workspace/01_slang_analysis.md` 존재 확인.

### Phase 2: 한국 신조어 매핑

```
Agent(
  subagent_type: "trend-monitor",
  model: "opus",
  prompt: "_workspace/01_slang_analysis.md를 읽고 한국 신조어 매핑을 실행하라.
           후보 3개 + 추천 1개를 포함하여 _workspace/02_korean_mapping.md에 저장하라."
)
```

### Phase 3: 검수

```
Agent(
  subagent_type: "sensitivity-checker",
  model: "opus",
  prompt: "_workspace/02_korean_mapping.md를 읽고 번역 후보 전체를 검수하라.
           플랫폼별 사용 가능 여부 포함하여 _workspace/03_final_translation.md에 저장하라."
)
```

### Phase 4: 결과 보고

`_workspace/03_final_translation.md`를 읽어 사용자에게 다음 형식으로 보고:

```
## 번역 결과

**원문:** [원문]
**최종 번역:** [번역]

**대안 후보:**
- [후보1]
- [후보2]
- [후보3]

**검수 등급:** [통과/주의/수정됨]
**플랫폼:** 유튜브 ✅ | 틱톡 ✅ | ...
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| Phase 1 실패 (의미 불명) | 가능한 해석 복수 제시 후 Phase 2 진행 |
| Phase 2 실패 (매핑 없음) | "의역 설명형" 번역으로 전환 |
| Phase 3 모두 사용 불가 | Sensitivity-Checker가 직접 대안 생성 |
| 원문이 여러 표현 포함 | 표현별로 각각 파이프라인 실행 |

## 테스트 시나리오

### 정상 흐름
1. 입력: `"it's giving main character energy"`
2. Phase 1: 자기 중심적·드라마틱한 태도, TikTok 유래, 감탄 톤
3. Phase 2: "주인공 각", "레전드 등장", "본인이 주인공인 줄" 등 후보
4. Phase 3: 전부 통과, "주인공 각" 최종 추천
5. 결과: `"주인공 각이네"` (유튜브/틱톡 모두 사용 가능)

### 재번역 흐름
1. 사용자: "다른 표현 없어?"
2. Phase 0: `_workspace/` 존재 + 재번역 요청 → Trend-Monitor부터 재실행
3. 새 후보 제시 후 검수
