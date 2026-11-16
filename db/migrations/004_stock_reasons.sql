-- 머니메이트 004_stock_reasons.sql  (작성: A)
-- C 요청: 탭 2 종목 상세 카드 ②(이유)·③(지금은)을 저장할 표. 근거는 docs/modules/overlap_api.md "부족한 점"(reasons.py 가 DB 에 저장하지 않음).
-- 규칙은 docs/conventions.md P19. 워커(reasons.py)가 쓰고 서버는 status = 'published' 만 읽는다.
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/004_stock_reasons.sql

BEGIN;

-- ============================================================
-- 종목 이유 카드 (C 가 씀, 탭 2 가 읽음)
-- ============================================================
-- 13F 분기마다 종목당 한 줄. 다시 생성하면 같은 (분기, 종목) 줄을 덮어쓰고 updated_at 을 바꾼다.
CREATE TABLE stock_reasons (
    big_period_end DATE        NOT NULL,          -- 13F 기준일 (overlap_results.big_period_end, 예: 2026-09-30)
    ticker         TEXT        NOT NULL,          -- 미국 티커 (conventions 1장)
    -- 종목 하나의 방향. overlap_results.direction 은 (큰손, ETF) 쌍마다 있어서, 종목 단위로 줄이는 규칙은
    -- reasons.py 를 부르는 쪽(C)이 정해 docs/modules/reasons.md 에 적는다
    direction      TEXT        NOT NULL CHECK (direction IN ('same', 'diff', 'none')),
    change         TEXT        NOT NULL CHECK (change IN ('up', 'down')),   -- 큰손 쪽 변화 (reasons.headline 의 두 번째 값)
    headline       TEXT        NOT NULL,          -- 카드 ② 제목 ("왜 다 늘렸을까요?" 등, reasons.headline 결과)
    reasons        JSONB       NOT NULL,          -- 카드 ②: 이유 1~3개 (제목·본문·인과 경로·경로 방향·근거 자료 id·날짜)
    now_view       JSONB,                         -- 카드 ③: 지금은 (아직 만들지 않았으면 NULL)
    status         TEXT        NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'published', 'rejected')),
    model_info     JSONB,                         -- 사용 모델·호출 수 (cards.model_info 와 같은 용도)
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (big_period_end, ticker)
);
-- 종목 상세는 티커로 가장 최근 분기를 찾는다
CREATE INDEX idx_stock_reasons_ticker ON stock_reasons (ticker, big_period_end DESC);

COMMENT ON COLUMN stock_reasons.status IS
    'reasons.py 의 errors 가 비면 published, 남으면 rejected (P19). 서버는 published 만 읽는다';

COMMIT;
