-- 머니메이트 003_etf_sources_cards.sql  (작성: A)
-- B(ETF 확인 결과)·C(1차 자료 전환) 요청 반영. 근거는 docs/findings.md B칸·C칸, 규칙은 docs/conventions.md P3·P6·P15~P18.
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/003_etf_sources_cards.sql

BEGIN;

-- ============================================================
-- holdings_etf (B 담당)
-- ============================================================
-- 수량은 1CU(설정 단위) 기준이라 소수가 온다 (KoAct NVIDIA 99.88).
ALTER TABLE holdings_etf
    ALTER COLUMN shares TYPE NUMERIC USING shares::NUMERIC;

-- pykrx 구성종목 코드는 티커가 아니라 CUSIP 2~7번째 글자 (NVIDIA 67066G104 -> 7066G1).
-- raw_code 에 받은 그대로 넣고, ticker 는 변환 후 채운다 (못 찾으면 NULL).
-- 기존 행이 있으면 ticker 로 채워 두고 수집기가 다시 덮어쓴다.
ALTER TABLE holdings_etf
    ADD COLUMN raw_code TEXT;
UPDATE holdings_etf SET raw_code = ticker WHERE raw_code IS NULL;
ALTER TABLE holdings_etf
    ALTER COLUMN raw_code SET NOT NULL,
    ALTER COLUMN ticker DROP NOT NULL;

-- ticker 가 NULL 이면 UNIQUE 로 중복을 못 막아서 raw_code 기준으로 바꾼다 (P6).
ALTER TABLE holdings_etf
    DROP CONSTRAINT holdings_etf_etf_code_snapshot_date_ticker_key,
    ADD CONSTRAINT holdings_etf_etf_code_snapshot_date_raw_code_key
        UNIQUE (etf_code, snapshot_date, raw_code);
CREATE INDEX idx_hetf_raw_code ON holdings_etf (raw_code);   -- 13F cusip 2~7번째 글자와 맞출 때

-- 1CU 기준 수량은 자금이 들어와도 늘지 않아 자금 유입 보정이 필요 없다. 방향 판정은 trend_chg_pct 로 한다 (P3).
ALTER TABLE holdings_etf
    DROP COLUMN trend_adj_pct;
ALTER TABLE overlap_results
    RENAME COLUMN etf_trend_adj_pct TO etf_trend_chg_pct;

-- ============================================================
-- 1차 자료 (C 담당). 초안: docs/modules/sources.md
-- ============================================================
-- 본문은 저장하지 않는다. 제목·원문 링크·날짜·카드에 쓸 숫자만.
CREATE TABLE raw_sources (
    id             BIGSERIAL PRIMARY KEY,
    source_type    TEXT NOT NULL CHECK (source_type IN ('dart', 'sec_8k', 'macro')),
    source_key     TEXT NOT NULL,                -- DART rcept_no / 8-K accession / 거시 event_id
    category       TEXT NOT NULL,                -- supply_contract, earnings, buyback, capex, material_agreement, fomc, bok_rate
    title          TEXT NOT NULL,
    url            TEXT NOT NULL,                -- 원문 링크
    issuer_name    TEXT,
    ticker         TEXT,                         -- 반응을 볼 대상: 국내 6자리 / 미국 티커 / 지수 키
    market         TEXT CHECK (market IN ('KR', 'US', 'INDEX')),
    published_date DATE NOT NULL,                -- 그 시장 날짜
    published_at   TIMESTAMPTZ,                  -- 시각을 모르면 NULL (DART)
    numbers        JSONB NOT NULL DEFAULT '{}',  -- 카드에 쓸 숫자 (금리 전·후 등)
    collected_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_type, source_key)
);
CREATE INDEX idx_raw_sources_published ON raw_sources (published_date DESC);

-- ============================================================
-- 카드 ↔ 1차 자료 (C 담당)
-- ============================================================
-- 같은 사건 자료 여러 개를 한 카드로 묶는다. 대표 자료(is_main)는 카드당 1개.
CREATE TABLE card_sources (
    card_id    BIGINT  NOT NULL REFERENCES cards (id) ON DELETE CASCADE,
    source_id  BIGINT  NOT NULL REFERENCES raw_sources (id),
    is_main    BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (card_id, source_id)
);
CREATE UNIQUE INDEX uq_card_sources_main ON card_sources (card_id) WHERE is_main;
CREATE INDEX idx_card_sources_source ON card_sources (source_id);

-- 네이버 뉴스를 쓰지 않으므로 카드는 raw_news 대신 card_sources 로 출처를 찾는다.
ALTER TABLE cards
    DROP COLUMN news_id;

-- ============================================================
-- steps (C 담당)
-- ============================================================
-- 판단 단계는 모든 유형에서 judgement 하나. AI 분석은 judgement 제출 후 채점 결과 화면이라 단계가 아니다.
ALTER TABLE steps
    DROP CONSTRAINT steps_kind_check,
    ADD CONSTRAINT steps_kind_check
        CHECK (kind IN ('concept', 'quiz', 'causal_order', 'chart', 'judgement'));

-- ============================================================
-- user_answers (A 담당): 루브릭 9점
-- ============================================================
COMMENT ON COLUMN user_answers.rubric IS
    '판단 채점 기준별 점수. 증거 0~2, 추론 0~4, 반박 0~3 (합계 9점). 예: {"evidence":2,"reasoning":3,"rebuttal":1}';
COMMENT ON COLUMN user_answers.score IS
    '판단 채점 100점 환산 (루브릭 9점 합계를 코드가 환산). 60점 이상이면 user_concepts 에 맞음으로 기록 (P17)';

COMMIT;
