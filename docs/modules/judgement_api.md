> **초안 (Claude 작성, 2026-11-05).** 담당자 A가 읽고 고쳐서 확정한다.

# server: POST /api/judgement (com.moneymate.judgement)

- **한 줄 설명**: 판단해보기 근거를 받아 FastAPI 채점 서버(worker/judge_api.py)에 채점을 맡기고, 결과를 `user_answers`에 저장해 돌려준다 (#55 2차).
- **입력**: JSON `{userId(UUID), stepId, choice(선택, 채점 안 함), answer(필수, 2000자 이하)}`. 빈 답안은 400.
- **하는 일** (`JudgementService`): ① 단계 확인(없거나 judgement가 아니면 404) ② 하루 제한: 오늘(KST 0시~) 그 사용자의 판단 답안 수가 `JUDGEMENT_DAILY_LIMIT`(기본 30) 이상이면 429 ③ 해시 재사용: SHA-256(stepId + 공백을 정리한 답안). 같은 해시의 **Claude 채점(`graded_by='llm'`)** 결과가 있으면 FastAPI를 부르지 않는다 ④ FastAPI `/judge` 호출(개념 id는 SQL에서 이름·별칭 JSON으로 바꿔 보냄) ⑤ `user_answers` 저장(`is_correct` = 60점 이상, P17).
- **출력**: `{score, correct, rubric{evidence,reasoning,rebuttal}, reasons, grader("claude"/"rule"), reused, message}`. FastAPI가 실패하면(연결·시간 초과·5xx) 점수는 null, `message`에 고정 문구를 넣고, 답안은 점수 없이 저장한다.
- **주의할 점**: 새 테이블 없이 `user_answers`(answer_hash, idx_uans_user_day)를 쓴다. 규칙 채점 결과는 재사용하지 않는다(Claude가 실패했을 때 것이라 다음에 다시 채점). 재사용한 응답은 `reasons`가 비어 있다(이유를 저장하는 칸이 없음, #56 피드백과 함께 정할 것). `users`에 없는 userId는 이 API가 넣는다. **P17 `recordConceptResult`(B)는 아직 없어서 부르지 않는다**(Service의 TODO). MyBatis 기본형은 `javaType="_long"`·`"_int"`(`long`은 Long이다).
- **실행**: `cd server && ./gradlew bootRun` (Windows: `gradlew.bat bootRun`). DB(`docker compose up -d db`)와 채점 서버(`docker compose up -d judge`)가 먼저 떠 있어야 한다. 설정은 `src/main/resources/application.yml`, 환경변수 `JUDGE_API_URL`·`JUDGEMENT_DAILY_LIMIT`·`POSTGRES_*`.
- **테스트**: `./gradlew test` (DB·FastAPI 없이 가짜로): `JudgementServiceTest`(Claude 채점 저장, 60점 기준, 해시 재사용, 하루 제한, KST 0시, 채점 서버 실패 고정 문구, 없는 단계), `AnswerHasherTest`, `JudgeClientTest`(snake_case·JSON 배열 요청, 응답 파싱, 5xx·빈 응답). 2026-11-05 실제 DB + judge 컨테이너로 정상·재사용·429·404·400·채점 서버 꺼짐을 확인하고 시험 데이터는 지웠다.
