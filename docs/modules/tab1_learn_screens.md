> **초안 (Claude 작성, 2026-10-28, 서버 연결 2026-11-07).** 담당자 C가 읽고 고쳐서 확정한다.

# web/src/pages/tab1 — 카드뉴스·단계형 학습·결과 화면

- **한 줄 설명**: 뉴스 홈에서 카드를 누르면 카드뉴스(2~3장) → 단계형 학습 → 결과 화면으로 이어지는 탭1 흐름. `VITE_USE_MOCK=false`면 Spring 서버, 아니면(기본) 목 데이터와 목 채점으로 돈다(데모 대비책).
- **입력**: `api/news.ts`의 `useNewsHome()` → `GET /api/news/home?userId=`, `api/cards.ts`의 `useCard(cardId)` → `GET /api/cards/{id}`, 답안 제출 `useSubmitAnswer()` → 퀴즈·차트·인과 순서는 `POST /api/answers`(C), 판단해보기는 `POST /api/judgement`(A). 목이면 `api/mocks/`. 타입은 `types/card.ts` (DB `cards.slides`, `steps.kind·content`와 맞춤).
- **하는 일**: 주소 `/news/:cardId`(카드뉴스) → `/news/:cardId/learn`(단계) → `/news/:cardId/result`(결과). 단계 화면은 `steps.kind`별로 나뉜다: concept(ConceptView), quiz·chart(QuizView), causal_order(CausalOrderView), judgement(ReasonView, 모든 유형의 마지막 단계). 단계 종류는 003 기준 5종이고 AI 분석은 단계가 아니다. 결과 화면은 개념 이해도(코드 채점 정답률), 적용 판단(루브릭 점수), 종합(둘의 평균), 학습 요약, AI 분석(판단해보기 채점 결과, 루브릭 9점: 증거 0~2·추론 0~4·반박 0~3), 13F·ETF로 이동(유형 3은 `/etf?ticker=NVDA`)을 보여 준다.
- **출력**: 화면. 채점 결과는 `store/learnStore.ts`(zustand)에 카드별로 담고 결과 화면이 읽는다.
- **주의할 점**: 정답(`steps.answer`)은 화면 데이터에 없다. 개발 중에는 `vite.config.ts`의 프록시가 `/api`를 `API_PROXY_TARGET`(기본 `http://localhost:8080`)으로 넘겨서 CORS 설정이 필요 없다(`VITE_API_BASE_URL`은 비워 둠). 답을 내면 홈을 다시 불러와 "학습 완료"가 바로 바뀐다. 서버는 `chgPct`·`sourcePublishedAt`이 null일 수 있어 홈이 `-`·생략으로 보여 준다. 차트 단계의 `startDate`·`endDate`는 #71 이후 출제한 카드에만 있다. 판단해보기는 선택이 아니라 근거만 채점하고, 근거는 20자 이상 필수. 차트 칸은 B의 `pages/tab1/steps/ChartStep.tsx`로 바꿀 자리(`QuizView`의 `ChartSlot`). 결과는 새로고침하면 사라진다(서버 `user_answers`가 원본이 될 예정). 홈의 "학습 완료" 배지는 서버 `completedCardIds`(concept 제외 모든 단계에 답) 값이다.
- **테스트**: 2026-10-28 Claude가 브라우저(375×812)에서 목 카드 3개를 끝까지 눌러 확인. 유형 2(퀴즈 1개 틀림 → 개념 이해도 67, 판단 43 → 종합 55), 유형 3(주관식 → AI 분석 → NVDA 종목 상세 링크), 유형 1(근거 20자 미만이면 제출 버튼 꺼짐). 이때 개념 단계 버튼이 클릭 이벤트를 결과로 넘겨 점수가 50으로 틀리던 버그를 찾아 `StepFrame`에서 고침. `pnpm lint`·`pnpm build` 통과.
  2026-11-07 Claude가 브라우저(375×812)에서 실제 서버(#74+#76, pending 카드 1장)로 홈 → 카드뉴스 3장 → 퀴즈 오답(정답·해설 표시) → 인과 순서 정답 → 차트 정답 → 판단해보기(채점 서버 꺼짐 → 고정 문구) → 결과 → 홈 "1 / 1 학습"·"학습 완료"까지 확인하고 시험 답안은 지웠다. `tsc -b`·`vite build`·`eslint`·`prettier --check` 통과.
