> **초안 (Claude 작성, 2026-11-24).** 담당자 사람2가 읽고 고쳐서 확정한다.

# worker/learner/state.py

- **한 줄 설명**: 사용자 × 개념의 알 확률을 `user_concept_state`(009)에 읽고 쓴다 (계획 2-3). 계산은 `learner/bkt.py`가 하고, 사람1 튜터의 가짜 `FakeMastery`(`tutor/mastery.py`) 자리에 들어간다.
- **입력**: DB 연결 `conn`, 사용자 UUID 문자열, 개념(노드 이름 또는 인과 사전 id), 정답 여부, 추측 확률.
- **하는 일**:
  - `get_mastery(conn, user_id)`: 개념 지도의 모든 노드에 대해 `{이름: 알 확률}`. 아직 안 풀어 본 개념은 처음 값 0.3.
  - `update(conn, user_id, concept, correct, guess_p)`: 개념 퀴즈(튜터·복습) 답 하나를 반영. `concept`은 노드 이름(label)이고, 없는 이름이면 `UnknownConcept`.
  - `update_causal(conn, user_id, causal_ids, correct, guess_p)`: 본 문제(퀴즈·차트 읽기·인과 순서) 답 하나를 그 단계의 인과 사전 개념(`steps.content.concept_ids`)마다 반영. 그 개념의 노드가 없으면 `concepts`의 이름으로 만들고(`causal_id`로 이음), 이름이 같은 노드가 이미 있으면 그 노드에 잇는다. 그래서 개념 퀴즈와 본 문제의 답이 같은 알 확률에 쌓인다.
- **출력**: `get_mastery`는 dict, `update`는 새 알 확률, `update_causal`은 `{인과 사전 id: 새 알 확률}`.
- **주의할 점**: 커밋하지 않는다. 부르는 쪽이 `with get_conn() as conn:`으로 묶어 답 기록과 함께 저장되거나 함께 취소되게 한다. 같은 사용자의 답이 동시에 와도 하나씩 반영되게 행을 잠근다(`FOR UPDATE`). `users`에 없는 사용자는 넣는다. 인과 사전에 없는 id와 중복 id는 건너뛴다 (`ConceptResultRecorder`와 같은 기준). `confidence` 인자는 받기만 하고 BKT에는 쓰지 않는다 (FSRS 2-4가 쓸 자리). 기존 `user_concepts(correct, total)`는 건드리지 않는다. Spring이 부를 FastAPI 엔드포인트는 아직 없다.
- **테스트**: 실제 PostgreSQL(009 적용)이 필요하고 끝에 모두 되돌린다. DB가 없으면 건너뛴다. Windows에서 psycopg DLL이 막히면 Docker로: `docker compose run --rm --no-deps -v "$(pwd -W)/worker:/app" judge sh -c "pip install -q pytest; python -m pytest tests/test_learner_state.py -q"` (5개: 새 사용자 처음 값, BKT 손계산과 개념별·사용자별 분리, 없는 개념, 인과 개념 노드 한 번만 만들기, 이름이 같은 노드에 잇기).

## 복습 일정 연결 (2026-11-24, 계획 2-4)
- **달라진 것**: 답 하나가 들어오면 알 확률(BKT)과 함께 복습 일정(FSRS, `learner/schedule.py`)도 고친다. `update`·`update_causal`에 `confidence`(1 헷갈려요 / 2 확실해요, 화면 글자도 받음), `response_ms`, `answer_changes`, `kind`, `now`를 줄 수 있다. 위 "주의할 점"의 "confidence는 받기만 한다"는 이제 복습 일정의 자동 평가에 쓴다로 바뀌었다 (알 확률에는 여전히 안 쓴다).
- **저장**: `user_concept_state`의 `stability`, `difficulty`, `last_review_at`, `due_at`, `fsrs_state`(늘 2), `sure_wrong_at`(010). 확실해요로 틀리면 `sure_wrong_at`에 시각을 남기고, 그 개념을 맞히면 지운다. 헷갈려요로 틀린 것은 남기지 않는다.
- **빨랐나**: 같은 종류의 문제를 맞혔던 지난 응답 시간(최근 50개)과 비교한다. 본 문제는 `user_answers`를 단계 종류로, 개념 퀴즈는 `concept_answers`를 퀴즈 종류로 모은다. Spring은 답안을 커밋한 뒤 부르므로 지금 낸 답도 비교 기록에 들어 있다.
- **`due_reviews(conn, user_id, now, limit=5)`**: 복습일이 오늘(KST 날짜)이거나 지난 개념 중에서 ① 확실해요라고 했는데 틀린 개념(최근 것부터) ② 나머지는 지금 기억 확률이 낮은 것부터, 하루 상한만큼. 상한은 개념 수 기준이고 오늘 이미 복습한 개념 수(`concept_answers`의 `source = 'review'`)를 뺀다. `{limit, done_today, due_total, items}`를 돌려준다.
- **주의할 점**: 복습일은 시각이 아니라 KST 날짜로 비교한다 (저녁에 푼 개념이 이틀 뒤 아침에 안 뜨는 일을 막는다). 복습 퀴즈를 내고 답을 `concept_answers`에 남기는 화면·API는 아직 없다 (마이페이지 2-7, 사람1의 퀴즈 출제와 연결).
- **테스트 추가** (같은 파일, 실제 DB): 답을 넣으면 일정이 잡힘(Good 2일·Hard 1일), 확실해요 + 틀림 표시와 지우기, 빠르고 확실하고 안 바꾼 답만 Easy, 복습 순서·하루 상한·오늘 복습한 수 빼기, KST 날짜 비교. 010이 적용된 DB가 필요하고 Docker에서는 `pip install fsrs`가 더 필요하다 (이미지를 다시 빌드하면 들어 있다).
