> **초안 (Claude 작성, 2026-11-24).** 담당자 사람2가 읽고 고쳐서 확정한다.

# 복습 문제 풀기 (worker learner/review.py + server LearnerController + web ReviewPage)

- **한 줄 설명**: 마이페이지 "오늘의 복습" 순서대로 개념마다 **새 문제를 하나씩** 내고, 답을 채점해서 알 확률(BKT)과 다음 복습일(FSRS)을 고친다 (계획 2-4의 "같은 개념을 매번 새 문제로", 2-7).
- **입력**: `POST /api/learner/review/quiz` `{userId, nodeId}`, `POST /api/learner/review/answer` `{userId, quizId, answer(고른 보기 번호), confidence(1·2), responseMs, answerChanges}`. Spring은 userId를 확인(UserGuard)하고 채점 서버의 `/learner/review/quiz`·`/learner/review/answer`로 그대로 전한다. 화면 주소는 `/mypage/review`.
- **하는 일 (worker)**
  - **낼 수 있는지 확인** (`review.prepare`): 그 개념이 오늘 복습 목록(`state.due_reviews`)에 있어야 한다. 없으면 409. 목록이 복습일과 하루 상한(5개)을 지키므로 LLM 호출 수도 같이 묶인다.
  - **종류 고르기** (`pick_kind`): 그 개념으로 지금까지 낸 복습 문제 수에 따라 용어 뜻 → 틀린 설명 → O/X 를 돌아가며 낸다. 문장도 매번 새로 만들어져서 같은 문제를 외워서 맞히기 어렵다.
  - **출제**: 사람1의 `tutor/quiz.py` `generate`(Haiku, 모양 검사, 찍어서 맞힐 확률 계산)를 그대로 쓴다. 개념 설명(`desc`)은 노드의 설명 → 없으면 카드 개념 단계가 같은 용어(이름·별칭)를 풀이한 문장 → 그것도 없으면 빈 글 순서로 넘긴다.
  - **보관** (`review.save`): 보기 순서를 코드가 섞고 정답 번호를 따라 옮긴 뒤, 문제와 정답을 `concept_quizzes`(011)에 넣는다. 화면에는 정답·해설 없이 `{quiz_id, node_id, concept, kind, content, guess_p}`만 나간다. 안 푼 문제가 남아 있으면 새로 만들지 않고 그 문제를 다시 준다.
  - **채점** (`review.answer`): 보관한 정답과 비교 → `state.update`(알 확률, 복습 일정, 확실해요인데 틀림 표시) → `concept_answers`에 `source = review`로 기록 → 문제에 답한 시각. 한 트랜잭션이다.
- **하는 일 (web)**: `ReviewQueueCard`의 [복습 시작] → `ReviewPage`. 들어온 순간의 목록으로 개념마다 문제를 받아 본 문제 퀴즈와 같은 화면(보기 고르기 → [헷갈려요] [확실해요] → 정답·해설·다음 복습일 → 다음 개념)으로 푼다. 끝나면 개념마다 맞힘·틀림과 다음 복습일을 보여 준다. 문제를 못 만들었으면 [다시 시도]나 건너뛰기를 고른다.
- **출력**: 문제는 `{quizId, nodeId, concept, kind, content{question | statement, options}, guessP}`, 채점은 `{correct, key, explanation, concept, pKnow, dueAt}`.
- **기준을 정한 이유**
  - **정답을 서버가 보관** (011 `concept_quizzes`): 정답을 화면에 내려보내지 않는다는 기존 규칙(본 문제와 같음)을 지키려면 문제를 낸 뒤 답이 올 때까지 서버가 정답을 들고 있어야 한다. `concept_answers`는 `is_correct`가 필수라 답하기 전 문제를 넣을 수 없어 표를 따로 뒀다.
  - **종류 세 가지만**: 화면 A(보기 고르기) 가운데 개념 하나로 낼 수 있는 것만 골랐다. 헷갈리는 쌍은 이웃 개념 목록이, 화면 B(칩 빈칸·짝 맞추기·사례 분류)는 화면이 아직 없다.
  - **보기 섞기**: LLM이 정답을 특정 자리에 두는 버릇이 있어도 찍어서 맞힐 확률이 `1 / 보기 수`가 되게 코드가 섞는다 (O/X 는 늘 O, X 순서).
- **주의할 점**: 정의를 묻는 문제는 정답이 맞는지 코드가 계산할 수 없다 (사람1 `tutor_quiz.md`와 같은 한계). 설명이 빈 개념은 LLM 지식에 기댄다. 지금 복습 대상은 대부분 인과 사전 개념이고 사전에는 설명이 없어서, 개념 지도(`concept_map.json`)가 `concept_nodes`에 들어오면 그 설명이 쓰인다. 문제 만들기는 2~3초 걸리고(실측 2.4초, 1문제 약 $0.00016) 월 한도에 걸리거나 모양 검사에 두 번 실패하면 503이다. Spring은 이 요청만 30초까지 기다린다. 복습일이 아닌 개념은 풀 수 없다 (자유 연습 없음). 같은 사용자가 같은 개념 문제를 동시에 두 번 요청하면 문제가 두 개 만들어질 수 있고, 그때는 나중 것을 쓴다. 인증은 Spring이 하고 채점 서버 주소는 밖에 열지 않는다.
- **테스트**: `cd worker && python -m pytest tests/test_learner_review.py tests/test_learner_api.py -q` (`test_learner_review` 9개: 종류 순서, 보기 섞기, 복습 목록에 없는 개념 거절, 설명 대체, 정답 숨김과 같은 문제 재사용, 채점 뒤 상태·기록·오늘 복습 수, 확실해요로 틀리면 맨 앞·다음 종류, 남의 문제. `test_learner_api` 복습 5개: 새 문제, 재사용 때 LLM 안 부름, 409, 503, 채점 전달과 404·409·422). `cd server; .\gradlew.bat test`의 `LearnerStateClientTest` 3개, `LearnerControllerTest` 3개 추가. 2026-11-24 Claude가 브라우저(375×812, 목)에서 5개 개념을 끝까지 풀어 세 종류 화면과 요약을 확인했고, 실제 서버(Spring 8081 → 채점 서버 8001 → PostgreSQL, 실제 LLM 2번)로 문제 받기, 다시 받으면 같은 문제(LLM 안 부름), 헷갈려요로 맞힘 → 알 확률 0.149 → 0.388·3일 뒤, 확실해요로 틀림 → 1일 뒤, 이미 답한 문제·복습 끝난 개념 409, 없는 문제 404, 오늘 복습 수 증가를 확인했다. 확인한 행은 지웠다.
