> **초안 (Claude 작성, 2026-10-28).** 담당자 C가 읽고 고쳐서 확정한다.

# web/src/pages/tab1 — 카드뉴스·단계형 학습·결과 화면 (목 데이터)

- **한 줄 설명**: 뉴스 홈에서 카드를 누르면 카드뉴스(2~3장) → 단계형 학습 → 결과 화면으로 이어지는 탭1 흐름. 지금은 목 데이터와 목 채점으로 돈다.
- **입력**: `api/cards.ts`의 `useCard(cardId)`(지금은 `api/mocks/cardDetail.ts`), 답안 제출 `useSubmitAnswer()`. 타입은 `types/card.ts` (DB `cards.slides`, `steps.kind·content`와 맞춤).
- **하는 일**: 주소 `/news/:cardId`(카드뉴스) → `/news/:cardId/learn`(단계) → `/news/:cardId/result`(결과). 단계 화면은 `steps.kind`별로 나뉜다: concept(ConceptView), quiz·chart(QuizView), causal_order(CausalOrderView), judgement·open_ended(ReasonView), ai_analysis(바로 앞 주관식의 AiAnalysis). 결과 화면은 개념 이해도(코드 채점 정답률), 적용 판단(루브릭 점수), 종합(둘의 평균), 학습 요약, AI 분석, 13F·ETF로 이동(유형 3은 `/etf?ticker=NVDA`)을 보여 준다.
- **출력**: 화면. 채점 결과는 `store/learnStore.ts`(zustand)에 카드별로 담고 결과 화면이 읽는다.
- **주의할 점**: 정답(`steps.answer`)은 화면 데이터에 없다. 목 채점(`answerMocks`, `mockRubricGrade`)은 서버가 생기면 `POST /api/answers`(C)·`/api/judgement`(A)로 바꾼다. 판단해보기는 선택이 아니라 근거만 채점하고, 근거는 20자 이상 필수. 차트 칸은 B의 `pages/tab1/steps/ChartStep.tsx`로 바꿀 자리(`QuizView`의 `ChartSlot`). 결과는 새로고침하면 사라진다(서버 `user_answers`가 원본이 될 예정). 홈의 "학습 완료" 배지는 아직 목 데이터 값 그대로다.
- **테스트**: 2026-10-28 Claude가 브라우저(375×812)에서 목 카드 3개를 끝까지 눌러 확인. 유형 2(퀴즈 1개 틀림 → 개념 이해도 67, 판단 43 → 종합 55), 유형 3(주관식 → AI 분석 → NVDA 종목 상세 링크), 유형 1(근거 20자 미만이면 제출 버튼 꺼짐). 이때 개념 단계 버튼이 클릭 이벤트를 결과로 넘겨 점수가 50으로 틀리던 버그를 찾아 `StepFrame`에서 고침. `pnpm lint`·`pnpm build` 통과.
