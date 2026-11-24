-- 머니메이트 010_sure_wrong.sql  (사람2, docs/추가구현_계획.md 2-4·2-5)
-- 복습 순서용 칸 하나. 복습 목록은 "확실해요라고 했는데 틀린" 개념을 맨 앞에 둔다 (과잉 수정 효과).
--   sure_wrong_at  이 개념을 확실해요(confidence = 2)로 내고 틀린 마지막 시각. 그 뒤 이 개념을 맞히면 NULL 로 지운다
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/010_sure_wrong.sql

BEGIN;

ALTER TABLE user_concept_state ADD COLUMN sure_wrong_at TIMESTAMPTZ;

COMMIT;
