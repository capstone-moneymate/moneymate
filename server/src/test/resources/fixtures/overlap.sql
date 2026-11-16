-- 겹침 API 통합 테스트용 샘플 (OverlapApiIntegrationTest). 001~003 마이그레이션 뒤에 실행된다.
-- overlap_results 는 아래 13F·ETF 값을 worker/compute/overlap.py build_results 에 넣어 나온 값 그대로다.
--   손계산: KoAct(0015B0) NVDA 99.88 -> 104.874 = +0.05, TIME(426030) NVDA 239 -> 200 = -0.16318 (6자리 반올림)
--           0015B0 GOOGL 50 -> 55 = +0.1
--   druckenmiller NVDA +0.1(늘림) vs +0.05(늘림) = same, vs -0.16318(줄임) = diff
--   thiel NVDA new(늘림, chg_pct NULL) vs 같은 두 ETF = same / diff
--   ackman GOOGL -0.25(줄임) vs +0.1(늘림) = diff
--   buffett AAPL 은 ETF 가 갖고 있지 않아 겹침 행이 없다.

INSERT INTO holdings_13f (filer_key, filer_cik, filer_name, period_end, filed_at, cusip, ticker, issuer_name,
                          shares, prev_shares, chg_pct, change_type) VALUES
    ('druckenmiller', '0001536411', 'Duquesne Family Office LLC', '2026-06-30', '2026-08-14',
     '67066G104', 'NVDA', 'NVIDIA CORPORATION', 1100, 1000, 0.1, 'increase'),
    ('thiel', '0001562087', 'Thiel Macro LLC', '2026-06-30', '2026-08-13',
     '67066G104', 'NVDA', 'NVIDIA CORPORATION', 500, NULL, NULL, 'new'),
    ('ackman', '0002026053', 'Pershing Square Inc.', '2026-06-30', '2026-08-14',
     '02079K305', 'GOOGL', 'ALPHABET INC', 750, 1000, -0.25, 'decrease'),
    ('buffett', '0001067983', 'Berkshire Hathaway Inc', '2026-06-30', '2026-08-14',
     '037833100', 'AAPL', 'APPLE INC', 1000, 1000, 0, 'unchanged');

INSERT INTO holdings_etf (etf_code, snapshot_date, raw_code, ticker, stock_name, shares,
                          trend_chg_pct, day_chg_pct, trend_base_date) VALUES
    ('0015B0', '2026-07-01', '7066G1', 'NVDA',  'NVIDIA CORP',   99.88,   NULL,     NULL,  NULL),
    ('0015B0', '2026-11-13', '7066G1', 'NVDA',  'NVIDIA CORP',   104.874, 0.05,     0.01,  '2026-07-01'),
    ('426030', '2026-07-01', '7066G1', 'NVDA',  'NVIDIA CORP',   239,     NULL,     NULL,  NULL),
    ('426030', '2026-11-13', '7066G1', NULL,    'NVIDIA CORP',   200,     -0.16318, -0.02, '2026-07-01'),
    ('0015B0', '2026-07-01', '2079K3', 'GOOGL', 'ALPHABET INC-CL A', 50, NULL,     NULL,  NULL),
    ('0015B0', '2026-11-13', '2079K3', 'GOOGL', 'ALPHABET INC-CL A', 55, 0.1,      0,     '2026-07-01');

-- 가장 최근 계산일(2026-11-14)만 내려가야 한다. 2026-11-13 행은 읽히면 안 된다.
INSERT INTO overlap_results (calc_date, ticker, filer_key, big_period_end, big_chg_pct,
                             etf_code, etf_snapshot_date, etf_trend_chg_pct, direction) VALUES
    ('2026-11-13', 'NVDA',  'druckenmiller', '2026-06-30', 0.1,   '0015B0', '2026-11-12', 0.01,     'none'),
    ('2026-11-14', 'NVDA',  'druckenmiller', '2026-06-30', 0.1,   '0015B0', '2026-11-13', 0.05,     'same'),
    ('2026-11-14', 'NVDA',  'druckenmiller', '2026-06-30', 0.1,   '426030', '2026-11-13', -0.16318, 'diff'),
    ('2026-11-14', 'NVDA',  'thiel',         '2026-06-30', NULL,  '0015B0', '2026-11-13', 0.05,     'same'),
    ('2026-11-14', 'NVDA',  'thiel',         '2026-06-30', NULL,  '426030', '2026-11-13', -0.16318, 'diff'),
    ('2026-11-14', 'GOOGL', 'ackman',        '2026-06-30', -0.25, '0015B0', '2026-11-13', 0.1,      'diff');
