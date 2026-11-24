-- 011: 낸 개념 퀴즈 보관 (사람2, docs/추가구현_계획.md 2-4·2-7 복습 문제 풀기)
--
-- 복습 문제는 그때그때 만들어져서(worker/tutor/quiz.py) steps 에 없다. 정답은 화면에 내려보내지 않으므로
-- 문제를 낸 순간부터 답이 올 때까지 서버가 정답을 들고 있어야 한다. 그 자리를 만든다.
-- 답이 오면 채점해서 concept_answers(009)에 남기고 answered_at 을 채운다.
-- 아직 안 푼 문제가 있으면 다시 들어와도 같은 문제를 보여 준다 (새로 고칠 때마다 LLM 을 부르지 않게).
--   source       tutor = 카드 앞 개념 단계, review = 복습 (concept_answers.source 와 같다)
--   quiz_kind    퀴즈 종류 (worker/tutor/quiz.py 의 종류 이름)
--   guess_p      찍어서 맞힐 확률 (코드 계산)
--   content      화면에 보여 주는 부분 (정답 없음)
--   answer_key   정답. 서버만 본다
--   explanation  답한 뒤 보여 주는 해설
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/011_concept_quizzes.sql

BEGIN;

CREATE TABLE concept_quizzes (
    id           BIGSERIAL PRIMARY KEY,
    user_id      UUID    NOT NULL REFERENCES users (id),
    node_id      BIGINT  NOT NULL REFERENCES concept_nodes (id),
    source       TEXT    NOT NULL CHECK (source IN ('tutor', 'review')),
    quiz_kind    TEXT    NOT NULL,
    guess_p      REAL    NOT NULL CHECK (guess_p BETWEEN 0 AND 1),
    content      JSONB   NOT NULL,
    answer_key   JSONB   NOT NULL,
    explanation  TEXT    NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    answered_at  TIMESTAMPTZ
);
CREATE INDEX idx_cquiz_user_node ON concept_quizzes (user_id, node_id, created_at);

COMMIT;
