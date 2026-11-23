> **초안 (Claude 작성, 2026-11-07).** 담당자 C가 읽고 고쳐서 확정한다.

# server: POST /api/answers (com.moneymate.answer)

- **한 줄 설명**: 탭1의 간단 퀴즈·차트 읽기·인과 순서 답을 `steps.answer`의 정답과 코드로 비교해 채점하고, `user_answers`에 저장한 뒤 결과·해설·정답을 돌려준다. 판단해보기는 A의 `POST /api/judgement`가 맡는다.
- **입력**: JSON `{userId(UUID), stepId(숫자, 문자열 "10"도 됨), answer}`. `answer`는 web `AnswerInput` 그대로: quiz·chart는 `{kind, optionIndex(0부터)}`, causal_order는 `{kind, order[개념 id]}`.
- **하는 일** (`AnswerService`): ① 단계 확인: 없거나 카드가 보여 줄 상태가 아니면 404. 뉴스 API와 같은 규칙으로 기본은 published, `NEWS_INCLUDE_PENDING=true`면 pending도 ② 입력 확인(400): judgement 단계, 단계와 다른 kind, 보기 번호 범위 밖(`content.options` 개수 기준), 순서에 빠뜨림·중복·다른 개념 ③ 채점: quiz·chart는 `optionIndex == answer.correct`, causal_order는 `order`가 `answer.correct`와 순서까지 같으면 정답 ④ 저장: `user_answers`(answer `{"kind","option_index"}` 또는 `{"kind","order"}`, `is_correct`, `graded_by='code'`). `users`에 없는 userId는 넣는다 ⑤ 개념 학습 기록(P17): B의 `ConceptResultRecorder.recordConceptResult(userId, steps.content.concept_ids, 채점 결과)`를 부른다. 탭 3 인과 지도·다시 보는 개념이 이 `user_concepts`를 읽는다.
- **출력**: `{stepId(문자열), isCorrect, explanation, correct}`. `correct`는 quiz·chart면 정답 보기 번호, causal_order면 정답 개념 id 순서다. 맞든 틀리든 항상 준다(제출한 뒤라 화면이 정답·해설을 보여 줌). 에러는 `{"message": ...}`.
- **주의할 점**: 정답은 출제 때 compose.py가 코드로 확인한 값이라 여기서는 비교만 한다. 저장된 정답이 없거나 형식이 다르면(출제 쪽 문제) 저장하지 않고 500. 같은 단계를 여러 번 내면 줄이 여러 개 쌓인다(뉴스 홈의 완료 카드는 서로 다른 단계 수로 센다). 개념 기록은 답안 저장과 같은 트랜잭션이라 기록이 실패하면 답안 저장도 취소된다. 400·404로 거절한 답은 기록하지 않는다. 같은 단계를 다시 내면 낼 때마다 센다(B 결정). 사전에 없는 개념 id는 recorder가 건너뛰고 경고 로그만 남긴다.
- **테스트**: `cd server; .\gradlew.bat test` (DB 없이 가짜 Repository) `AnswerServiceTest` 16개 (recorder도 가짜): 퀴즈 정답 저장(answer JSON·code), 오답일 때 정답 번호, 차트, 보기 번호 범위 밖·없음 400 미저장, 인과 순서 정답·순서 바뀜 오답, 빠뜨림·중복·다른 개념 400, judgement → /api/judgement 안내, kind 다름 400, 없는 단계 404, pending 설정 전달, 깨진 정답 500 미저장, 응답 JSON 이름(`isCorrect`)과 문자열 stepId 읽기, 개념 기록(정답 → 단계 개념 id·true, 오답 → false, 400·404로 거절한 답은 기록 안 함). 2026-11-07 실제 DB(pending 카드 1장, `NEWS_INCLUDE_PENDING=true`)로 퀴즈·인과 순서 정답/오답, 차트 정답 200과 `user_answers` 저장 형식(`code`), 보기 범위 밖·판단해보기·잘못된 UUID 400, 없는 단계 404(400·404는 저장 안 됨)를 확인하고 시험 데이터는 지웠다. 2026-11-16 같은 카드로 퀴즈 정답·인과 순서 오답·차트 정답을 내서 `user_concepts`가 rate_hold 2/3, growth_valuation 0/1로 쌓이고(400·404는 안 쌓임) `GET /api/mypage/map`에 learned로 나오는 것을 확인하고 시험 데이터는 지웠다.

## GET /api/answers/history (2026-11-21, 탭3 풀었던 내용 보기)
- **입력**: `?userId=<UUID>&cardId=<id>&date=yyyy-MM-dd`(선택, KST). userId 확인은 UserGuard(계정 UUID면 로그인 세션 필요).
- **하는 일** (`AnswerHistoryService`): 이 카드에서 단계마다 마지막 답안을 고른다(`DISTINCT ON step_id`, 날짜를 주면 그날 낸 답안 중에서). 코드 채점 단계는 저장된 답(`option_index`·`order`)과 `steps.answer`의 정답·해설을, 판단해보기는 고른 문장·근거와 저장된 점수·루브릭·피드백(`user_answers.feedback`의 `{feedback, reasons}`)을 `/api/judgement` 응답 모양(JudgementGrade)으로 돌려준다.
- **출력**: `[{stepId, input:{kind, optionIndex | order | choice, reason}, result:{stepId, isCorrect, explanation, correct, grade}}]`, 단계 번호 순. 그날 안 푼 단계는 빠진다. 기록이 없으면 빈 배열.
- **주의할 점**: 읽기 전용. 정답·해설은 답을 낸 단계만 내려간다(답을 낼 때 이미 보여 준 값). 판단해보기는 선택지 번호가 저장돼 있지 않아 화면이 문장으로 찾는다. 점수가 없는 판단 답안은 `message`("이 답안은 채점하지 못했어요.")만 채운다.
- **테스트**: `AnswerHistoryServiceTest` 5개(퀴즈 고른 보기·정답, 인과 순서, 판단 점수·루브릭·피드백, 채점 못 한 판단, 빈 기록). SQL은 2026-11-21 로컬 PostgreSQL에서 트랜잭션 안에 같은 단계 답 3개(KST 11/20 두 번, 11/21 한 번)와 판단 답 1개를 넣고 date=11/20으로 돌려 11/20의 나중 답(보기 1)과 판단 줄만 나오는 것을 확인 후 ROLLBACK.

## 확신·응답 시간·답 변경 저장 + 알 확률 갱신 (2026-11-24, 추가 구현 2-1·2-2·2-3)
- **입력 추가**: `{userId, stepId, answer, confidence, responseMs, answerChanges}`. `confidence`는 정답을 보기 전에 누른 확신(1 헷갈려요, 2 확실해요), `responseMs`는 문제가 화면에 뜬 순간부터 낼 때까지, `answerChanges`는 내기 전에 답을 바꾼 횟수. 셋 다 화면이 재서 보내고, 안 보내도 된다(null 저장). `confidence`가 1·2가 아니거나 음수가 오면 400.
- **하는 일 추가**: 채점에는 쓰지 않고 `user_answers`의 `confidence`·`response_ms`·`answer_changes`(009)에 저장만 한다. 답안이 커밋된 뒤 `LearnerStateClient`로 채점 서버 `/learner/answer`를 불러 그 단계 개념의 알 확률을 고친다 (`docs/modules/learner_api.md`). 실패해도 채점 응답은 같다.
- **주의할 점**: `attempt_no`는 아직 안 넣는다(기본 1). 다시 풀기를 시도별로 나누는 것은 계획 1-4에서 한다. 기존 `user_concepts`(correct, total) 기록은 그대로 한다.
- **테스트**: `AnswerServiceTest`에 4개 추가(확신·시간 저장, 퀴즈는 보기 수·인과 순서는 개념 수를 넘김, 잘못된 답은 안 넘김).
