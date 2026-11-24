> **초안 (Claude 작성, 2026-11-24).** 담당자 사람2가 읽고 고쳐서 확정한다.

# 마이페이지 "내 학습" 탭 (server LearnerController + web ReviewQueueCard·ConfidenceCard)

- **한 줄 설명**: 마이페이지에 세 번째 탭 "내 학습"을 더해 오늘의 복습(FSRS 복습 목록)과 확신 점검(2 × 2 표)을 보여 준다 (계획 2-7). 숫자는 모두 채점 서버(`worker/learner`)가 계산하고, Spring은 전달만, 화면은 표기만 한다.
- **입력**: `GET /api/learner/reviews?userId=<UUID>`, `GET /api/learner/calibration?userId=<UUID>`. userId 확인은 UserGuard(계정 UUID면 로그인 세션 필요). 화면 주소는 `/mypage?view=learn`.
- **하는 일 (server, `com.moneymate.learning`)**: `LearnerController`가 userId를 확인한 뒤 `LearnerStateClient.reviews` / `calibration`으로 채점 서버의 `/learner/reviews/{user}` / `/learner/calibration/{user}`를 부른다. 채점 서버의 snake_case(`due_total`)를 `LearnerDtos` 레코드(@JsonAlias)로 읽어 화면에는 camelCase(`dueTotal`)로 내보낸다. 채점 서버가 꺼져 있거나 실패하면 503과 `{"message": ...}`.
- **하는 일 (web)**: `MyPage`의 탭이 달력 / 내 학습 / 인과 지도 세 개가 된다. `ReviewQueueCard`는 서버가 준 순서 그대로(확실하다고 했는데 틀린 개념 먼저, 나머지는 기억 확률 낮은 순) 개념 이름·이유·기억 확률(%)을 보여 주고, 하루 상한과 더 남은 개수를 적는다. `ConfidenceCard`는 "확실해요라고 한 답 중 N%를 맞혔어요", 2 × 2 개수 표("확실해요인데 틀림" 칸만 붉게), 최근 30일과 그 전의 비교, 확실하다고 했는데 틀린 개념 목록을 보여 준다. 두 카드는 따로 불러와서 한쪽이 실패해도 다른 쪽은 보인다.
- **출력**: `reviews`는 `{limit, doneToday, dueTotal, items: [{nodeId, concept, pKnow, retrievability, reason, dueAt}]}`, `calibration`은 `{all, recent, earlier, recentDays, sureWrongConcepts}` (각 요약은 개수 4개와 비율. 분모가 0이면 null).
- **주의할 점**: 답이 충분하지 않으면(`enough = false`, 20개 미만) 비율은 숨기고 개수만 보여 준다. 최근·이전 비교는 두 기간 모두 충분할 때만 나온다. 화면에는 gamma·bias 같은 용어를 쓰지 않고 정답률과 개수로만 말한다 (값은 응답에 들어 있다). 복습 문제는 "오늘의 복습" 카드의 [복습 시작]에서 푼다 (`/mypage/review`, `docs/modules/learner_review.md`). 푼 답이 `concept_answers`(source = review)에 남아 하루 상한이 줄어든다. 기존 "다시 보는 개념"(`ReviewList`, `/api/mypage/review`)은 화면에서 이미 쓰지 않고 있어 그대로 뒀다. 고스트 비교(2-6)는 시도 번호(1-4)가 들어온 뒤에 한다.
- **테스트**: `cd server; .\gradlew.bat test` `LearnerStateClientTest`에 3개 추가(snake_case 읽기, 분모 0은 null 그대로, 조회 실패는 예외), `LearnerControllerTest` 4개(전달, 로그인 필요한 계정은 채점 서버를 안 부름, 실패는 503). 2026-11-24 Claude가 브라우저(375×812, 목)에서 `/mypage?view=learn`의 두 카드와 탭 전환을 확인했고, 실제 서버(Spring 8081 → 채점 서버 8001 → PostgreSQL)로 답 3개를 넣은 뒤 두 API를 불러 camelCase 응답·"확실해요인데 틀린 개념 먼저" 순서·null 처리를 확인했다. 확인한 행은 지웠다.
