-- 머니메이트 001_init.sql  (초안 v0.1, 작성: A)
-- 문서의 13개 테이블 + cusip_map(기술확정안·분담표에 "cusip_map 테이블에 캐시"라고만 있고 13개 목록엔 없음 -> 14번째로 추가)
-- 규칙은 docs/conventions.md 를 따른다. 컬럼은 일요일 싱크에서 B·C와 확정한다. 바꿀 땐 002_... 로 추가한다.
-- 시간대: 모든 TIMESTAMPTZ는 UTC 저장, 화면에서 KST 변환.

BEGIN;

-- ============================================================
-- 1. 뉴스 (C 담당)
-- ============================================================
CREATE TABLE raw_news (
    id             BIGSERIAL PRIMARY KEY,
    title          TEXT        NOT NULL,
    url            TEXT        NOT NULL UNIQUE,
    press          TEXT,                         -- 언론사
    published_at   TIMESTAMPTZ,                  -- 기사 시각
    keyword        TEXT,                         -- 어떤 감시 키워드로 잡혔나
    keyword_type   TEXT CHECK (keyword_type IN ('stock', 'sector', 'macro')),
    description    TEXT,                         -- API가 주는 요약(원문 본문은 저장하지 않는다)
    collected_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_raw_news_published ON raw_news (published_at DESC);

-- ============================================================
-- 2. 가격·지수 (C 담당)
-- ============================================================
CREATE TABLE prices (
    ticker       TEXT    NOT NULL,               -- NVDA / '005930' / 'KS11' ...
    market       TEXT    NOT NULL CHECK (market IN ('US', 'KR', 'INDEX')),
    market_date  DATE    NOT NULL,               -- 그 시장의 거래일
    open         NUMERIC,
    high         NUMERIC,
    low          NUMERIC,
    close        NUMERIC NOT NULL,
    volume       BIGINT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker, market_date)
);

-- ============================================================
-- 3. CUSIP -> 티커 캐시 (A 담당)  [13개 목록 밖, 14번째]
-- ============================================================
CREATE TABLE cusip_map (
    cusip        TEXT PRIMARY KEY,
    ticker       TEXT,                           -- 못 찾으면 NULL
    issuer_name  TEXT,
    source       TEXT NOT NULL DEFAULT 'openfigi',
    resolved_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 4. 13F 큰손 보유 (A 담당)
-- ============================================================
CREATE TABLE holdings_13f (
    id            BIGSERIAL PRIMARY KEY,
    filer_key     TEXT   NOT NULL,               -- buffett / druckenmiller / thiel / ackman
    filer_cik     TEXT   NOT NULL,               -- 10자리 문자열
    filer_name    TEXT   NOT NULL,               -- 실제 제출 법인명
    period_end    DATE   NOT NULL,               -- 분기 말 (예: 2026-06-30)
    filed_at      DATE   NOT NULL,               -- 공시일
    accession_no  TEXT,
    cusip         TEXT   NOT NULL,
    ticker        TEXT,                          -- cusip_map 으로 채움, 못 찾으면 NULL
    issuer_name   TEXT,
    shares        BIGINT NOT NULL,               -- SharesPrnAmount (옵션 PUT/CALL·채권 제외하고 저장)
    prev_shares   BIGINT,                        -- 직전 분기 수량 (holdings_change.py 가 채움)
    chg_pct       NUMERIC,                       -- 0.05 = +5%. 직전 분기에 없으면 NULL
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (filer_cik, period_end, cusip)
);
CREATE INDEX idx_h13f_ticker ON holdings_13f (ticker, period_end);

-- ============================================================
-- 5. 액티브 ETF 보유 (B 담당)
-- ============================================================
CREATE TABLE holdings_etf (
    id               BIGSERIAL PRIMARY KEY,
    etf_code         TEXT   NOT NULL,            -- '426030' (6자리 문자열)
    snapshot_date    DATE   NOT NULL,            -- 보유 내역 기준 거래일
    ticker           TEXT   NOT NULL,            -- 구성종목 코드 (미국주식이면 NVDA 형식)
    stock_name       TEXT,
    shares           BIGINT NOT NULL,
    source           TEXT   NOT NULL DEFAULT 'pykrx'
                     CHECK (source IN ('pykrx', 'provider_file', 'manual')),
    trend_chg_pct    NUMERIC,                    -- 분기 말 대비 (추세)
    day_chg_pct      NUMERIC,                    -- 전 거래일 대비 (어제)
    trend_adj_pct    NUMERIC,                    -- 자금 유입 보정 후 (종목 변화율 - 전체 중앙값)
    collected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (etf_code, snapshot_date, ticker)
);
CREATE INDEX idx_hetf_ticker ON holdings_etf (ticker, snapshot_date);

-- ============================================================
-- 6. 겹침 결과 (A 담당, 탭2가 읽음)
-- ============================================================
CREATE TABLE overlap_results (
    id               BIGSERIAL PRIMARY KEY,
    calc_date        DATE   NOT NULL,            -- 계산한 날
    ticker           TEXT   NOT NULL,
    filer_key        TEXT   NOT NULL,
    big_period_end   DATE   NOT NULL,            -- 사용한 13F 분기 말
    big_chg_pct      NUMERIC,
    etf_code         TEXT   NOT NULL,
    etf_snapshot_date DATE  NOT NULL,
    etf_trend_adj_pct NUMERIC,
    direction        TEXT   NOT NULL CHECK (direction IN ('same', 'diff', 'none')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (calc_date, ticker, filer_key, etf_code)
);

-- ============================================================
-- 7. 인과 뼈대: 개념 사전 (B가 적재)
-- ============================================================
CREATE TABLE concepts (
    id        TEXT PRIMARY KEY,                  -- rate_hold 같은 영문 id
    name      TEXT NOT NULL,                     -- 기준금리 동결
    theme     TEXT NOT NULL,                     -- 금리 / AI·반도체 / 차트 읽기
    kind      TEXT,                              -- B가 정함 (예: 사건/지표/결과)
    aliases   TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE causal_edges (
    id            BIGSERIAL PRIMARY KEY,
    from_concept  TEXT NOT NULL REFERENCES concepts (id),
    to_concept    TEXT NOT NULL REFERENCES concepts (id),
    force_dir     TEXT NOT NULL CHECK (force_dir IN ('up', 'down')),   -- 올리는 힘 / 누르는 힘
    note          TEXT,
    UNIQUE (from_concept, to_concept)
);

-- ============================================================
-- 8. 카드·단계 (C 담당, 탭1이 읽음)
-- ============================================================
CREATE TABLE cards (
    id             BIGSERIAL PRIMARY KEY,
    card_date      DATE     NOT NULL,            -- 노출 날짜
    news_id        BIGINT   REFERENCES raw_news (id),
    card_type      SMALLINT NOT NULL CHECK (card_type IN (1, 2, 3)),
    status         TEXT     NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'published', 'rejected')),
    title          TEXT     NOT NULL,
    slides         JSONB    NOT NULL,            -- 카드뉴스 2~3장
    start_concept  TEXT     REFERENCES concepts (id),
    ticker         TEXT,                         -- 유형 3이면 연결 종목 (예: NVDA)
    key_facts      JSONB,                        -- 출제 때 만든 핵심 사실 목록 (증거 채점에 사용)
    source_links   JSONB,                        -- 원문 링크들
    model_info     JSONB,                        -- 사용 모델·재생성 횟수
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at   TIMESTAMPTZ
);
CREATE INDEX idx_cards_date_status ON cards (card_date, status);

CREATE TABLE steps (
    id         BIGSERIAL PRIMARY KEY,
    card_id    BIGINT   NOT NULL REFERENCES cards (id) ON DELETE CASCADE,
    step_no    SMALLINT NOT NULL,
    kind       TEXT     NOT NULL CHECK (kind IN
               ('concept', 'quiz', 'causal_order', 'chart', 'judgement', 'open_ended', 'ai_analysis')),
    content    JSONB    NOT NULL,                -- 사용자에게 보이는 부분
    answer     JSONB,                            -- 저장된 정답 (사용자에게 내려보내지 않음)
    UNIQUE (card_id, step_no)
);

-- ============================================================
-- 9. 사용자·답안·학습 기록 (A·B·C가 서버 통해 씀)
-- ============================================================
CREATE TABLE users (
    id          UUID PRIMARY KEY,                -- 첫 실행 때 브라우저가 만든 익명 ID
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_answers (
    id           BIGSERIAL PRIMARY KEY,
    user_id      UUID   NOT NULL REFERENCES users (id),
    card_id      BIGINT NOT NULL REFERENCES cards (id),
    step_id      BIGINT NOT NULL REFERENCES steps (id),
    answer       JSONB  NOT NULL,
    answer_hash  TEXT,                           -- 같은 답안 채점 재사용용
    is_correct   BOOLEAN,                        -- 코드 채점 단계
    score        SMALLINT CHECK (score BETWEEN 0 AND 100),   -- 판단·주관식 100점 환산
    rubric       JSONB,                          -- {"evidence":2,"reasoning":3,"rebuttal":1}
    feedback     TEXT,
    graded_by    TEXT CHECK (graded_by IN ('code', 'rule', 'llm')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_uans_user_day ON user_answers (user_id, created_at);
CREATE INDEX idx_uans_hash ON user_answers (answer_hash);

CREATE TABLE user_concepts (
    user_id     UUID NOT NULL REFERENCES users (id),
    concept_id  TEXT NOT NULL REFERENCES concepts (id),
    correct     INTEGER NOT NULL DEFAULT 0,
    total       INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, concept_id)
);

-- ============================================================
-- 10. LLM 비용 로그 (C의 llm_client.py 와 A의 judge.py 가 씀)
-- ============================================================
CREATE TABLE llm_cost_log (
    id             BIGSERIAL PRIMARY KEY,
    called_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    module         TEXT    NOT NULL,             -- classify / compose / reasons / judge ...
    model          TEXT    NOT NULL,
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    cost_usd       NUMERIC(12, 6) NOT NULL DEFAULT 0,
    card_id        BIGINT REFERENCES cards (id),
    note           TEXT
);
CREATE INDEX idx_llm_cost_called ON llm_cost_log (called_at);

COMMIT;
