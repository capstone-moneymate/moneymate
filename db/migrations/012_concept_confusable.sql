-- 012: 헷갈리기 쉬운 이웃 개념 (사람1이 채우고 사람2의 복습 문제가 읽는다, docs/추가구현_계획.md 1-3 "헷갈리는 쌍")
--
-- 개념 지도에서 임베딩이 가까운 개념 쌍 가운데 사람이 검토해서 남긴 것만 넣는다
-- (임베딩만으로는 매출액 ↔ 시가총액 같은 엉뚱한 쌍이 섞인다).
-- "헷갈리는 쌍" 퀴즈(worker/tutor/quiz.py, pair=[개념, 이웃])가 이 표에서 이웃을 고른다.
--   node_id   기준 개념
--   other_id  그 개념과 헷갈리기 쉬운 이웃
--   sim       임베딩 유사도. 높을수록 더 헷갈린다 (이웃이 여럿이면 높은 것부터 쓴다)
-- 한 줄은 한 방향이다 ("node_id 를 볼 때 other_id 가 헷갈린다"). 서로 헷갈리는 쌍은 두 줄로 넣는다.
-- 노드를 지우면 그 노드가 낀 줄도 함께 지워진다.
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/012_concept_confusable.sql

BEGIN;

CREATE TABLE concept_confusable (
    node_id     BIGINT NOT NULL REFERENCES concept_nodes (id) ON DELETE CASCADE,
    other_id    BIGINT NOT NULL REFERENCES concept_nodes (id) ON DELETE CASCADE,
    sim         REAL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (node_id, other_id),
    CHECK (node_id <> other_id)
);
CREATE INDEX idx_confusable_other ON concept_confusable (other_id);

COMMIT;
