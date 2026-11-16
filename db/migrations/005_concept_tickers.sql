-- 머니메이트 005_concept_tickers.sql  (작성: A, #100)
-- 개념↔티커 매핑. 탭 2 종목 상세의 "내 지도에 있어요"(사용자가 배운 개념과 연결된 종목)에 쓴다.
-- 원본은 db/seeds/concept_tickers.csv 이고 worker/concepts/ticker_loader.py 가 CSV 와 똑같이 맞춘다 (conventions P20).
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/005_concept_tickers.sql

BEGIN;

CREATE TABLE concept_tickers (
    concept_id  TEXT        NOT NULL REFERENCES concepts (id),   -- B 의 개념 사전 id 만 (concepts.csv)
    ticker      TEXT        NOT NULL,
    market      TEXT        NOT NULL CHECK (market IN ('US', 'KR')),
    reason      TEXT        NOT NULL,                            -- 왜 이 종목이 이 개념에 해당하는지 (한 문장)
    source      TEXT        NOT NULL CHECK (source LIKE 'https://%'),   -- 근거 공시 링크 (10-K·20-F 등)
    status      TEXT        NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'approved')),         -- 팀 검토 전 draft, 검토 후 approved
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (concept_id, ticker),
    -- 티커 형식 (conventions 1장): 미국은 대문자, 클래스주는 하이픈 (BRK-B). 한국은 6자리 문자열 (영문 대문자 가능)
    CONSTRAINT concept_tickers_ticker_format CHECK (
        (market = 'US' AND ticker ~ '^[A-Z]+(-[A-Z]+)?$') OR
        (market = 'KR' AND ticker ~ '^[0-9A-Z]{6}$'))
);
-- 종목 상세는 티커로 연결된 개념을 찾는다
CREATE INDEX idx_concept_tickers_ticker ON concept_tickers (ticker);

COMMIT;
