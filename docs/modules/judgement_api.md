> **초안 (Claude 작성, 2026-11-05).** 담당자 A가 읽고 고쳐서 확정한다.

# server: POST /api/judgement (com.moneymate.judgement)

- **한 줄 설명**: 판단해보기 근거를 받아 FastAPI 채점 서버(worker/judge_api.py)에 채점과 AI 분석 피드백을 맡기고, 결과를 `user_answers`에 저장해 돌려준다 (#55 2차, #56).
- **입력**: JSON `{userId(UUID), stepId, choice(선택, 채점 안 함), answer(필수, 2000자 이하)}`. 빈 답안은 400.
- **하는 일** (`JudgementService`): ① 단계 확인(없거나 judgement가 아니면 404) ② 하루 제한: 오늘(KST 0시~) 그 사용자의 판단 답안 수가 `JUDGEMENT_DAILY_LIMIT`(기본 30) 이상이면 429 ③ 해시 재사용: SHA-256(stepId + 공백을 정리한 답안). 같은 해시의 **Claude 채점(`graded_by='llm'`)** 결과가 있으면 FastAPI를 부르지 않는다 ④ FastAPI `/judge` 호출(개념 id는 SQL에서 이름·별칭 JSON으로 바꿔 보냄) ⑤ `user_answers` 저장(`is_correct` = 60점 이상, P17). 피드백과 채점 이유는 `feedback`(TEXT) 칸에 `{"feedback": {...}, "reasons": {...}}` JSON 문자열로 저장한다(#56).
- **출력**: `{score, correct, rubric{evidence,reasoning,rebuttal}, reasons, grader("claude"/"rule"), reused, message, feedback{good, thinkMore, chain[{name, used}], chainComment}}`. 예시는 아래 "응답 예시". FastAPI가 실패하면(연결·시간 초과·5xx) 점수는 null, `message`에 고정 문구를 넣고, 답안은 점수 없이 저장한다.
- **주의할 점**: 새 테이블 없이 `user_answers`(answer_hash, idx_uans_user_day)를 쓴다. 규칙 채점 결과는 재사용하지 않는다(Claude가 실패했을 때 것이라 다음에 다시 채점). 재사용한 응답도 저장된 `feedback`·`reasons`를 그대로 돌려준다. #56 이전에 저장된 줄은 `feedback`이 null이라 재사용하면 `feedback: null`, `reasons: {}`이다. `users`에 없는 userId는 이 API가 넣는다. **P17 `recordConceptResult`(B)는 아직 없어서 부르지 않는다**(Service의 TODO). MyBatis 기본형은 `javaType="_long"`·`"_int"`(`long`은 Long이다).
- **실행**: `cd server && ./gradlew bootRun` (Windows: `gradlew.bat bootRun`). DB(`docker compose up -d db`)와 채점 서버(`docker compose up -d judge`)가 먼저 떠 있어야 한다. 설정은 `src/main/resources/application.yml`, 환경변수 `JUDGE_API_URL`·`JUDGEMENT_DAILY_LIMIT`·`POSTGRES_*`.
- **테스트**: `./gradlew test` (DB·FastAPI 없이 가짜로): `JudgementServiceTest`(Claude 채점 저장, 60점 기준, 해시 재사용과 피드백·이유 복원, #56 이전 줄 재사용, 깨진 JSON, 하루 제한, KST 0시, 채점 서버 실패 고정 문구, 없는 단계), `AnswerHasherTest`, `JudgeClientTest`(snake_case·JSON 배열 요청, snake_case 피드백 응답 파싱, 5xx·빈 응답). 2026-11-05 실제 DB + judge 컨테이너로 정상·재사용(피드백 포함)·429·404·400·채점 서버 꺼짐을 확인하고 시험 데이터는 지웠다.

## 응답 예시 (C의 결과 화면용)

바뀐 필드 (#56): **`feedback` 추가.** 기존 필드는 그대로이고, 재사용한 응답에도 `reasons`·`feedback`이 나온다. 웹에 내려가는 이름은 camelCase(`thinkMore`, `chainComment`)다.

화면에 쓰는 법: 잘한 점 = `feedback.good`, 더 생각할 점 = `feedback.thinkMore`, 인과 뼈대 = `feedback.chain`을 순서대로 이어 그리고 `used: false`인 개념을 흐리게(빠뜨린 개념) + 아래에 `feedback.chainComment`. `feedback`이 null이면 `message`만 보여 준다.

**1) Claude 채점** (`grader: "claude"`)
```json
{
  "score": 78, "correct": true,
  "rubric": {"evidence": 2, "reasoning": 4, "rebuttal": 1},
  "reasons": {"reasoning": "동결에서 은행 실적까지 잇고 금리 인하 상황까지 넓혔어요.", "rebuttal": "위험을 말했지만 판단과 이어지지 않았어요."},
  "grader": "claude", "reused": false, "message": null,
  "feedback": {
    "good": "기준금리 동결에서 은행 실적까지 원인과 결과를 이어서 썼어요.",
    "thinkMore": "경기 둔화처럼 판단을 뒤집을 수 있는 힘을 하나 더 생각해 보세요.",
    "chain": [{"name": "기준금리 동결", "used": true}, {"name": "예대금리차", "used": true}, {"name": "은행 실적", "used": true}],
    "chainComment": "동결이 예대금리차를 거쳐 은행 실적으로 이어지는 흐름을 잘 짚었어요."
  }
}
```
(문장은 예시다. 실제 Claude 문장은 API 키를 받은 뒤 확인한다.)

**2) 규칙 채점** (Claude 실패·한도 초과, `grader: "rule"`): 점수는 키워드 규칙, 문장은 고정 문구, 인과 뼈대는 코드 값
```json
{
  "score": 89, "correct": true,
  "rubric": {"evidence": 2, "reasoning": 3, "rebuttal": 3},
  "reasons": {}, "grader": "rule", "reused": false, "message": null,
  "feedback": {
    "good": "근거 있는 선택이었어요.",
    "thinkMore": "이런 경우도 생길 수 있어요.",
    "chain": [{"name": "기준금리 동결", "used": true}, {"name": "예대금리차", "used": false}, {"name": "은행 실적", "used": true}],
    "chainComment": "예대금리차까지 이어 보면 인과 뼈대가 완성돼요."
  }
}
```

**3) 채점 서버 실패** (FastAPI 꺼짐·시간 초과): 점수·피드백 없이 고정 문구
```json
{
  "score": null, "correct": null, "rubric": null, "reasons": {}, "grader": null,
  "reused": false, "message": "근거 있는 선택이었어요. 이런 경우도 생길 수 있어요.", "feedback": null
}
```

그 밖: 하루 제한 초과 429 `{"message": "오늘 판단 채점은 30번까지 할 수 있어요. 내일 다시 해 주세요."}`, 없는 단계 404 `{"message": ...}`, 빈 답안 400.
