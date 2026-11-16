> **초안 (Claude 작성, 2026-11-15).** 담당자 B가 읽고 고쳐서 확정한다.

# server: recordConceptResult (com.moneymate.learning)

- **한 줄 설명**: 채점 결과를 `user_concepts`(correct, total)에 쌓는 서버 공통 메서드 (conventions P17). 코드 채점(C, `AnswerService`)과 판단 채점(A, `JudgementService`)이 둘 다 이 메서드 하나를 불러서, 기록 기준이 하나가 된다.
- **입력**: `ConceptResultRecorder.recordConceptResult(String userId, String[] conceptIds, Boolean isCorrect)`. "맞음"은 부르는 쪽이 정한다 (코드 채점은 정답 일치, 판단은 60점 이상, P17).
- **하는 일**: ① isCorrect가 null(판단 채점을 못 함)이거나 conceptIds가 null·빈 배열이면 아무것도 하지 않는다 ② 빈 문자열을 빼고 같은 id는 한 번만 남긴다 (순서 유지) ③ `users`에 없는 userId는 넣는다 ④ 개념마다 total +1, 맞으면 correct +1 (`INSERT ... SELECT FROM concepts ... ON CONFLICT (user_id, concept_id) DO UPDATE`), `updated_at` 갱신.
- **출력**: 실제로 기록한 개념 수 (int).
- **주의할 점**: 같은 단계를 다시 내도 **낼 때마다 센다** (2026-11-15 B 결정. P17 메서드 모양 그대로, 여러 번 헷갈린 개념이 다시 보는 개념에 먼저 나오게). 판단 채점이 해시로 결과를 재사용할 때도 센다. `concepts`에 없는 id는 SQL이 `concepts`와 맞춰 보며 건너뛰고 경고 로그만 남긴다 (외래키 오류로 채점 응답이 깨지지 않게). 부르는 쪽의 `@Transactional` 안에서 함께 돈다. 이 메서드는 쓰기만 하고, 읽기(인과 지도·다시 보는 개념)는 마이페이지 API가 한다.
- **부르는 곳**: `AnswerService`·`JudgementService`의 `TODO(P17)` 자리. 두 파일은 각각 C·A 담당이라 그쪽에서 연결한다. 개념 id는 답안 API는 `steps.content.concept_ids`, 판단 채점 API는 `steps.answer.chain`에서 가져온다.
- **테스트**: `cd server; .\gradlew.bat test` (DB 없이 가짜 Repository) `ConceptResultRecorderTest` 7개: 맞음·틀림 기록, null 결과 미기록, 빈·null id 미기록, 중복 id 한 번만(순서 유지), 사전에 없는 id 예외 없음, 기록할 게 없으면 users도 안 건드림. 2026-11-15 일회용 PostgreSQL 16(migrations 001~003)에서 실제 mapper XML로 맞음(rate_hold·bank_profit·없는 id·중복 rate_hold) → 틀림(rate_hold) → null 순서로 불러 `bank_profit 1/1`, `rate_hold 1/2`, 없는 id 건너뜀, null 미기록을 확인했다 (임시 테스트라 레포에는 넣지 않음).
