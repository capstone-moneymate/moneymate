-- 머니메이트 006_card_debates.sql  (작성: A)
-- 판단해보기 AI 분석 피드백용 낙관·비관 토론. TradingAgents 대신 직접 만든다 (docs/tradingagents-trial.md "결론").
-- worker/generate/debate.py 가 카드마다 하루 1번 미리 쓰고, 서버는 판단 채점 때 status = 'published' 만 읽어
-- 채점 서버(judge_api.py)에 넘긴다. judge.py 가 "더 생각할 점"의 재료로 쓴다 (conventions P21).
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/006_card_debates.sql

BEGIN;

-- ============================================================
-- 카드 토론 (A 가 씀, 판단 채점이 읽음)
-- ============================================================
-- 카드당 한 줄. 다시 만들면 같은 card_id 줄을 덮어쓰고 updated_at 을 바꾼다.
CREATE TABLE card_debates (
    card_id     BIGINT      PRIMARY KEY REFERENCES cards (id) ON DELETE CASCADE,
    bull        TEXT,                                -- 낙관 에이전트 발언 (검사를 못 넘었으면 NULL 일 수 있음)
    bear        TEXT,                                -- 비관 에이전트 발언 (낙관 발언을 보고 반박)
    status      TEXT        NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'published', 'rejected')),
    model_info  JSONB,                               -- 모델·호출 수·비용·검사 실패 까닭
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- 게시한 토론은 두 발언이 다 있어야 한다
    CONSTRAINT card_debates_published_has_text CHECK (
        status <> 'published' OR (bull IS NOT NULL AND bear IS NOT NULL))
);

COMMENT ON COLUMN card_debates.status IS
    'debate.py 의 코드 검사(숫자·금지 표현·선택지 이름)를 두 발언이 모두 통과하면 published, 아니면 rejected (P21). 서버는 published 만 읽는다';

COMMIT;
