> **초안 (Claude 작성, 2026-11-25).** 담당자 사람1이 읽고 고쳐서 확정한다.

# server/src/main/java/com/moneymate/tutor (TutorController, TutorClient, TutorDtos)

- **한 줄 설명**: 화면이 부르는 튜터 API (#240). 로그인 사용자를 확인하고 채점 서버의 `/tutor`(worker/tutor/api.py)로 넘긴다. `LearnerController`와 같은 방식이다.
- **입력**: `POST /api/tutor/start {userId, cardId}`, `POST /api/tutor/{sessionId}/answer {userId, answer, confidence, responseMs, answerChanges}`, `GET /api/tutor/{sessionId}?userId=`. 답 응답은 채점 결과만 담고 status 가 `running` 이다(다음 퀴즈는 채점 서버가 뒤에서 만듦, #281). 화면은 GET 으로 다음 이벤트를 받는다. 세션의 로그인 userId 는 `UserGuard`로 확인한다(계정에 붙은 UUID 는 그 계정 로그인이어야 함).
- **하는 일**: 그대로 전달한다. 채점 서버가 snake_case(session_id)로 주면 화면에는 camelCase(sessionId)로 나간다(@JsonAlias). 이벤트 안의 키는 채점 서버 그대로다(guess_p 등).
- **출력**: `TutorState {sessionId, status, finishedBy, targets, quizzes, maxQuizzes, events}`. 실패는 `{"message": ...}`: 채점 서버가 꺼졌거나 시간이 넘으면 503, 없는 카드·세션 404, 기다리는 퀴즈 없음 409, 그 밖 400.
- **주의할 점**: 튜터는 한 요청에 모델을 여러 번 부르고 퀴즈도 만들어서 읽기 시간 초과를 90초로 길게 뒀다. 503·404가 오면 화면은 개념 단계를 건너뛰고 본 문제로 가면 된다(튜터가 없어도 카드는 풀 수 있게).
- **테스트**: `server` 에서 `./gradlew test --tests 'com.moneymate.tutor.*'` (TutorClientTest: 가짜 서버로 보내는 JSON(snake_case, 목록 답)·받는 모양·GET 쿼리·404 / TutorControllerTest: 확인된 사용자로 그대로 전달, 로그인 안 된 계정은 채점 서버를 안 부름, 404·409·400·503 바꾸기).
