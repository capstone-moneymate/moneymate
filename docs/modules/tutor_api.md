> **초안 (Claude 작성, 2026-11-25).** 담당자 사람1이 읽고 고쳐서 확정한다.

# worker/tutor/api.py

- **한 줄 설명**: 튜터 에이전트(#201, #230)를 채점 서버(judge_api)의 `/tutor` 라우터로 연다 (#240). Spring `TutorController`가 로그인 사용자를 확인한 뒤 부른다.
- **입력**: `POST /tutor/start {user_id, card_id}`, `POST /tutor/{session_id}/answer {user_id, answer, confidence(1·2, 선택), response_ms, answer_changes}`, `GET /tutor/{session_id}?user_id=`. 지도·목표 개념·카드 제목은 DB에서 읽는다(`ConceptMap.from_db`, `card_targets`).
- **하는 일**: 시작하면 세션을 만들고 퀴즈를 낼 때까지(또는 끝날 때까지) 튜터를 돌린다. 답이 오면 채점 → 알 확률·답 기록(사람2 BKT, `concept_answers`)까지 하고 **graded 만 바로 돌려준다(status `running`)**. 다음 퀴즈(또는 끝)는 뒤 스레드에서 만들고(그동안 세션 잠금, 같은 세션에 답이 오면 409), 화면이 GET 으로 받아 간다 (#281: 답 응답이 7~13초 → 0.1초). 답 응답에는 그 채점 결과만 담는다(그 전 이벤트는 화면이 GET 으로 이미 받음). GET 은 전부. 이벤트는 explain {concept, definition, detail, example}(example 은 빈 문자열일 수 있다), quiz {kind, concept, content, guess_p}(정답 없음), graded {concept, kind, correct, key, explanation}(답한 뒤라 정답 포함), done {by}. 개념 단계 용어가 지도에 없는 카드는 모델을 부르지 않고 `done(no_targets)`.
- **출력**: `{session_id, status(waiting/done/error), finished_by, targets, quizzes, max_quizzes, events}`.
- **주의할 점**: 세션은 이 서버 메모리(`SESSIONS`)에 있다. 서버를 다시 켜면 사라지고(화면은 본 문제로 넘어가면 됨), 2시간 안 쓰면 지우고, 500개를 넘으면 오래된 것부터 지운다. 여러 프로세스로 띄우면 세션이 나뉘니 채점 서버는 프로세스 하나로 띄운다. DB 연결은 알 확률을 읽고 답을 기록할 때만 잠깐 연다(`ShortConnMastery`): 한 요청 안에서 모델을 여러 번 불러 몇 초~수십 초 걸리기 때문이다. 남의 세션은 없는 세션처럼 404. 같은 세션에 답이 동시에 오면 409. 모델 호출이 실패하면 채점(graded)은 그대로 돌려주고 `done(stop:오류)`로 끝낸다.
- **테스트**: `cd worker && python -m pytest tests/test_tutor_api.py -q` (가짜 모델: 시작→퀴즈(정답 없음)→답→채점(정답 포함)·끝, 새 이벤트만/GET 전부, 남의·없는 세션·없는 카드 404, 기다리는 퀴즈 없음 409, 목표 없는 카드는 모델 안 부름, 모델 실패해도 채점·끝 이벤트, 확신 범위 422, 오래된 세션 지우기, 연결을 부를 때마다 열기).
