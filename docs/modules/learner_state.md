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
