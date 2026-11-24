> **초안 (Claude 작성, 2026-11-24).** 담당자 사람2가 읽고 고쳐서 확정한다.

# worker/learner/api.py (+ server LearnerStateClient)

- **한 줄 설명**: 본 문제(퀴즈·차트 읽기·인과 순서)를 채점한 Spring이 알 확률(BKT)을 고치라고 부르는 API (계획 2-3). 채점 서버(`judge_api.py`)에 라우터로 붙어서 같은 주소·같은 컨테이너를 쓴다.
- **입력**: `POST /learner/answer` `{user_id(UUID), concept_ids[인과 사전 id], correct, kind(quiz/chart/causal_order), count}`. `count`는 quiz·chart면 보기 수, causal_order면 놓을 개념 수. `GET /learner/mastery/{user_id}`.
- **하는 일**: 찍어서 맞힐 확률을 형식에서 계산한다(`guess_for_step`). 보기 고르기는 `1 / 보기 수`(4지선다 0.25), 인과 순서는 `1 / 개념 수!`(3개면 1/6). 그 값으로 `learner/state.update_causal`을 불러 개념마다 알 확률을 고친다. 채점은 하지 않는다.
- **출력**: `{guess_p, mastery: {인과 사전 id: 새 알 확률}}`. mastery 조회는 `{mastery: {개념 이름: 알 확률}}`.
- **부르는 쪽 (Spring)**: `com.moneymate.learning.LearnerStateClient.recordAnswer`. `AnswerService`가 답안을 저장하고 **커밋한 뒤에** 부른다. 채점 서버도 `users`에 같은 사용자를 넣으려 하므로, 트랜잭션 안에서 부르면 처음 답을 내는 사용자에서 서로를 기다린다. 주소는 `moneymate.judge.url`(판단 채점과 같음), 연결 2초·응답 3초. 실패하면 로그만 남기고 채점 응답은 그대로 나간다.
- **주의할 점**: 이 라우터만 DB를 읽고 쓴다 (판단 채점 `/judge`는 그대로 DB를 안 쓴다). psycopg는 요청이 올 때 불러와서, 채점 서버를 띄우는 것만으로는 DB가 필요 없다. 판단해보기(서술형)는 찍어서 맞힐 확률을 정할 수 없어 아직 알 확률에 반영하지 않는다. 인증이 없으니 채점 서버처럼 밖에 열지 않는다. 채점 서버가 꺼져 있으면 답은 저장되지만 알 확률은 안 바뀐다 (다시 맞추는 기능은 없다).
- **테스트**: `cd worker && python -m pytest tests/test_learner_api.py -q` (8개: 찍어서 맞힐 확률 손계산, 요청이 state로 넘어가는 값, 인과 순서 1/6, 잘못된 요청 4가지 422, mastery 조회). `cd server; .\gradlew.bat test`의 `LearnerStateClientTest` 3개(보내는 JSON 모양, 서버 오류 삼키기, 개념 없으면 안 부름). 2026-11-24 로컬에서 Spring(8081) → 채점 서버(8001) → PostgreSQL로 실제 카드 답 3개를 넣어 확인: 4지선다 맞힘 0.646 → 2개 인과 순서 틀림 0.341, 4지선다 틀림 0.149 (손계산과 같음). 확인한 행은 지웠다.

## 복습 일정용 추가 (2026-11-24, 계획 2-4)
- `POST /learner/answer`에 `confidence`(1·2), `response_ms`, `answer_changes`를 더 받는다 (없어도 됨). 알 확률과 함께 복습 일정을 고친다. Spring `LearnerStateClient.recordAnswer`가 답안의 값을 그대로 넘긴다.
- `GET /learner/reviews/{user_id}`: 오늘 복습할 개념. `{limit, done_today, due_total, items: [{node_id, concept, p_know, retrievability, reason(sure_wrong/due), due_at}]}`. 순서와 상한은 `docs/modules/learner_state.md`.
- 테스트: `test_learner_api.py` 13개(확신·시간 넘김, 안 보낸 요청, 범위 밖 값 422, 복습 목록). 2026-11-24 로컬에서 Spring(8081) → 채점 서버(8001) → PostgreSQL로 답 3개: 맞힘 + 확실해요 → 안정도 2.307·2일 뒤, 같은 개념을 같은 날 헷갈려요로 다시 맞힘 → 난이도만 오름, 틀림 + 확실해요 → 안정도 0.212·1일 뒤·`sure_wrong_at` 기록. 확인한 행은 지웠다.

## 복습 문제 풀기 추가 (2026-11-24, 계획 2-7)
- `POST /learner/review/quiz` `{user_id, node_id}` → `{quiz_id, node_id, concept, kind, content, guess_p}` (정답 없음). 오늘 복습할 개념이 아니면 409, 문제를 못 만들면 503.
- `POST /learner/review/answer` `{user_id, quiz_id, answer, confidence, response_ms, answer_changes}` → `{correct, key, explanation, concept, p_know, due_at}`. 없는 문제 404, 이미 답한 문제 409.
- 본 문제와 달리 이 둘은 채점 서버가 직접 내고 채점한다 (정답을 채점 서버가 보관해서). Spring `LearnerStateClient.reviewQuiz`는 LLM을 기다리느라 응답을 30초까지 기다리고, `LearnerController`가 채점 서버의 404·409를 그대로, 그 밖의 4xx는 400으로 전한다. 자세한 내용은 `docs/modules/learner_review.md`.
