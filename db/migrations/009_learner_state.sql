-- 머니메이트 009_learner_state.sql  (사람2, docs/추가구현_계획.md 2-1)
-- SW 차별점 추가 구현용 스키마: 답 기록 확장 + 개념 지도 + 학습자 상태.
--   1. user_answers  확신·응답 시간·답 변경 횟수·몇 번째 시도
--   2. concept_nodes / concept_node_cards / concept_prereq  사람1의 개념 지도 (logs/concept_map/concept_map.json 을 넣는 곳)
--   3. user_concept_state  사용자 × 개념의 알 확률(BKT)과 복습 일정(FSRS)
--   4. concept_answers  steps 에 없는 개념 퀴즈(튜터 진단, 복습)의 답 기록
-- 기존 user_concepts(correct, total)는 지우지 않는다. 새 상태가 안정되면 정리한다.
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/009_learner_state.sql

BEGIN;

-- ------------------------------------------------------------
-- 1. 답 기록 확장
-- ------------------------------------------------------------
--   confidence      1 애매해요, 2 확신해요. 판단해보기(서술형)와 이 기능 전의 답은 NULL
--   response_ms     문제가 화면에 뜬 순간 ~ 제출 (화면이 잰다). 안 보내면 NULL
--   answer_changes  제출 전에 답을 바꾼 횟수. 안 보내면 NULL
--   attempt_no      이 카드를 몇 번째로 푸는가 (1부터). 이 기능 전의 답은 모두 1
ALTER TABLE user_answers
    ADD COLUMN confidence     SMALLINT CHECK (confidence IN (1, 2)),
    ADD COLUMN response_ms    INTEGER  CHECK (response_ms >= 0),
    ADD COLUMN answer_changes INTEGER  CHECK (answer_changes >= 0),
    ADD COLUMN attempt_no     INTEGER  NOT NULL DEFAULT 1 CHECK (attempt_no >= 1);
CREATE INDEX idx_uans_user_card_attempt ON user_answers (user_id, card_id, attempt_no);

-- ------------------------------------------------------------
-- 2. 개념 지도 (사람1이 적재)
-- ------------------------------------------------------------
-- 퀴즈 앞 "개념" 단계 용어로 만든 노드. 탭 1 인과 사전(concepts 29개)과는 별개다.
--   label        대표 이름 ("EPS"). 다시 만들 때 같은 노드를 찾는 기준이라 UNIQUE
--   description  뜻풀이 (concept_map.json 의 desc)
--   aliases      같은 뜻으로 묶인 다른 표기 ("주당순이익")
--   causal_id    인과 사전 개념과 같은 것이면 그 id. 본 문제(steps.content.concept_ids)의 답으로도
--                같은 노드의 알 확률을 갱신하려고 둔다. 대부분 NULL
-- 노드를 지우면 사용자 상태가 걸려 있어 막힌다 (일부러). 다시 만들 때는 label 로 찾아 UPDATE 한다.
CREATE TABLE concept_nodes (
    id           BIGSERIAL PRIMARY KEY,
    label        TEXT NOT NULL UNIQUE,
    description  TEXT,
    aliases      TEXT[] NOT NULL DEFAULT '{}',
    causal_id    TEXT UNIQUE REFERENCES concepts (id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 어느 카드에 나온 용어인가 (concept_map.json 의 card_ids). 튜터가 "이 카드에 필요한 개념"을 찾는다
CREATE TABLE concept_node_cards (
    node_id  BIGINT NOT NULL REFERENCES concept_nodes (id) ON DELETE CASCADE,
    card_id  BIGINT NOT NULL REFERENCES cards (id) ON DELETE CASCADE,
    PRIMARY KEY (node_id, card_id)
);
CREATE INDEX idx_cnc_card ON concept_node_cards (card_id);

-- 선수 관계: post 를 이해하려면 pre 를 먼저 알아야 한다. votes / total = LLM 다수결 표 (예: 3 / 4)
CREATE TABLE concept_prereq (
    pre_id      BIGINT   NOT NULL REFERENCES concept_nodes (id) ON DELETE CASCADE,
    post_id     BIGINT   NOT NULL REFERENCES concept_nodes (id) ON DELETE CASCADE,
    votes       SMALLINT NOT NULL CHECK (votes >= 0),
    total       SMALLINT NOT NULL CHECK (total >= votes),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (pre_id, post_id),
    CHECK (pre_id <> post_id)
);
CREATE INDEX idx_prereq_post ON concept_prereq (post_id);

-- ------------------------------------------------------------
-- 3. 학습자 상태: 사용자 × 개념
-- ------------------------------------------------------------
--   p_know          알 확률 (BKT, 0~1)
--   stability       FSRS 안정도 (일). 복습 전이면 NULL
--   difficulty      FSRS 난이도 (1~10). 복습 전이면 NULL
--   fsrs_state      FSRS 카드 상태 (1 learning, 2 review, 3 relearning)
--   fsrs_step       learning / relearning 안에서 몇 번째 단계인가
--   last_review_at  마지막으로 이 개념 문제를 푼 시각
--   due_at          다음 복습 시각 (기억 확률이 목표치로 떨어지는 때)
CREATE TABLE user_concept_state (
    user_id         UUID   NOT NULL REFERENCES users (id),
    node_id         BIGINT NOT NULL REFERENCES concept_nodes (id),
    p_know          REAL   NOT NULL CHECK (p_know BETWEEN 0 AND 1),
    stability       REAL   CHECK (stability > 0),
    difficulty      REAL   CHECK (difficulty BETWEEN 1 AND 10),
    fsrs_state      SMALLINT CHECK (fsrs_state IN (1, 2, 3)),
    fsrs_step       SMALLINT CHECK (fsrs_step >= 0),
    last_review_at  TIMESTAMPTZ,
    due_at          TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, node_id)
);
CREATE INDEX idx_ucs_user_due ON user_concept_state (user_id, due_at);

-- ------------------------------------------------------------
-- 4. 개념 퀴즈 답 기록 (튜터 진단 퀴즈, 복습 퀴즈)
-- ------------------------------------------------------------
-- 이 문제들은 그때그때 만들어져 steps 에 없어서 user_answers(step_id NOT NULL)에 못 넣는다.
-- 확신 보정(2-5)은 user_answers 와 이 표를 합쳐서 계산한다.
--   source      tutor = 카드 앞 개념 단계, review = 복습
--   card_id     tutor 일 때 그 카드. review 는 NULL
--   attempt_no  tutor 일 때 그 카드의 몇 번째 시도 (고스트의 "개념 단계 N문제 필요")
--   quiz_kind   퀴즈 종류 (worker/tutor/quiz.py 의 7종류 이름)
--   guess_p     찍어서 맞힐 확률 (코드 계산, BKT 추측 확률로 쓴 값)
--   quiz        낸 문제 (화면용 content). answer = 사용자가 낸 답
CREATE TABLE concept_answers (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID    NOT NULL REFERENCES users (id),
    node_id         BIGINT  NOT NULL REFERENCES concept_nodes (id),
    source          TEXT    NOT NULL CHECK (source IN ('tutor', 'review')),
    card_id         BIGINT  REFERENCES cards (id),
    attempt_no      INTEGER CHECK (attempt_no >= 1),
    quiz_kind       TEXT    NOT NULL,
    guess_p         REAL    CHECK (guess_p BETWEEN 0 AND 1),
    quiz            JSONB,
    answer          JSONB,
    is_correct      BOOLEAN NOT NULL,
    confidence      SMALLINT CHECK (confidence IN (1, 2)),
    response_ms     INTEGER  CHECK (response_ms >= 0),
    answer_changes  INTEGER  CHECK (answer_changes >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_cans_user_day ON concept_answers (user_id, created_at);
CREATE INDEX idx_cans_user_node ON concept_answers (user_id, node_id, created_at);

COMMIT;
