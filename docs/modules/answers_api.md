> **초안 (Claude 작성, 2026-11-07).** 담당자 C가 읽고 고쳐서 확정한다.

# server: POST /api/answers (com.moneymate.answer)

- **한 줄 설명**: 탭1의 간단 퀴즈·차트 읽기·인과 순서 답을 `steps.answer`의 정답과 코드로 비교해 채점하고, `user_answers`에 저장한 뒤 결과·해설·정답을 돌려준다. 판단해보기는 A의 `POST /api/judgement`가 맡는다.
- **입력**: JSON `{userId(UUID), stepId(숫자, 문자열 "10"도 됨), answer}`. `answer`는 web `AnswerInput` 그대로: quiz·chart는 `{kind, optionIndex(0부터)}`, causal_order는 `{kind, order[개념 id]}`.
- **하는 일** (`AnswerService`): ① 단계 확인: 없거나 카드가 보여 줄 상태가 아니면 404. 뉴스 API와 같은 규칙으로 기본은 published, `NEWS_INCLUDE_PENDING=true`면 pending도 ② 입력 확인(400): judgement 단계, 단계와 다른 kind, 보기 번호 범위 밖(`content.options` 개수 기준), 순서에 빠뜨림·중복·다른 개념 ③ 채점: quiz·chart는 `optionIndex == answer.correct`, causal_order는 `order`가 `answer.correct`와 순서까지 같으면 정답 ④ 저장: `user_answers`(answer `{"kind","option_index"}` 또는 `{"kind","order"}`, `is_correct`, `graded_by='code'`). `users`에 없는 userId는 넣는다.
- **출력**: `{stepId(문자열), isCorrect, explanation, correct}`. `correct`는 quiz·chart면 정답 보기 번호, causal_order면 정답 개념 id 순서다. 맞든 틀리든 항상 준다(제출한 뒤라 화면이 정답·해설을 보여 줌). 에러는 `{"message": ...}`.
- **주의할 점**: 정답은 출제 때 compose.py가 코드로 확인한 값이라 여기서는 비교만 한다. 저장된 정답이 없거나 형식이 다르면(출제 쪽 문제) 저장하지 않고 500. 같은 단계를 여러 번 내면 줄이 여러 개 쌓인다(뉴스 홈의 완료 카드는 서로 다른 단계 수로 센다). **P17 `recordConceptResult`(B)는 아직 없어서 부르지 않는다**(Service의 TODO, `AnswerStep.conceptIds`에 개념 id를 준비해 둠).
- **테스트**: `cd server; .\gradlew.bat test` (DB 없이 가짜 Repository) `AnswerServiceTest` 13개: 퀴즈 정답 저장(answer JSON·code), 오답일 때 정답 번호, 차트, 보기 번호 범위 밖·없음 400 미저장, 인과 순서 정답·순서 바뀜 오답, 빠뜨림·중복·다른 개념 400, judgement → /api/judgement 안내, kind 다름 400, 없는 단계 404, pending 설정 전달, 깨진 정답 500 미저장, 응답 JSON 이름(`isCorrect`)과 문자열 stepId 읽기. 2026-11-07 실제 DB(pending 카드 1장, `NEWS_INCLUDE_PENDING=true`)로 퀴즈·인과 순서 정답/오답, 차트 정답 200과 `user_answers` 저장 형식(`code`), 보기 범위 밖·판단해보기·잘못된 UUID 400, 없는 단계 404(400·404는 저장 안 됨)를 확인하고 시험 데이터는 지웠다.
