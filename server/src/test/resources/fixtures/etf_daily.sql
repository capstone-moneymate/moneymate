-- ETF 어제 변화 API 통합 테스트용 샘플 (EtfApiIntegrationTest). 001~003 마이그레이션 뒤에 실행된다.
-- 기준값 0.05. 손계산:
--   늘림(>= 0.05): 0015B0 AMZN 0.20, 0015B0 NVDA 0.08, 426030 NVDA 0.06, 0015B0 GOOGL 0.05(경계 포함)
--     -> 가장 많이 늘림 TOP3 = AMZN 0.20, NVDA 0.08(0015B0), NVDA 0.06(426030)
--   줄임(<= -0.05): 426030 MSFT -0.30, 0015B0 AAPL -0.10, 426030 META -0.06
--     -> 가장 많이 줄임 TOP3 = MSFT, AAPL, META.  426030 AAPL -0.049999 는 줄임 아님
--   함께 늘림: 두 ETF 모두 늘린 NVDA 만 (GOOGL 은 426030 이 +0.01)
--   0015B0 TSLA 는 day_chg_pct NULL(어제 새로 담음)이라 안 나온다
--   426030 2026-11-12 의 AMZN 0.99 는 최신 스냅샷이 아니라 안 나온다

INSERT INTO holdings_etf (etf_code, snapshot_date, raw_code, ticker, stock_name, shares, day_chg_pct) VALUES
    ('426030', '2026-11-12', '023135', 'AMZN', 'AMAZON.COM INC',     10,  NULL),
    ('426030', '2026-11-12', '7066G1', 'NVDA', 'NVIDIA CORP',        226, NULL),
    ('0015B0', '2026-11-13', '7066G1', 'NVDA', 'NVIDIA CORP',        108, 0.08),
    ('0015B0', '2026-11-13', '2079K3', 'GOOGL', 'ALPHABET INC-CL A', 21,  0.05),
    ('0015B0', '2026-11-13', '037833', 'AAPL', 'APPLE INC',          45,  -0.10),
    ('0015B0', '2026-11-13', '594918', 'MSFT', 'MICROSOFT CORP',     51,  0.02),
    ('0015B0', '2026-11-13', '88160R', 'TSLA', 'TESLA INC',          5,   NULL),
    ('0015B0', '2026-11-13', '023135', 'AMZN', 'AMAZON.COM INC',     12,  0.20),
    ('426030', '2026-11-13', '7066G1', NULL,   'NVIDIA CORP',        240, 0.06),
    ('426030', '2026-11-13', '2079K3', 'GOOGL', 'ALPHABET INC-CL A', 101, 0.01),
    ('426030', '2026-11-13', '037833', 'AAPL', 'APPLE INC',          95,  -0.049999),
    ('426030', '2026-11-13', '594918', 'MSFT', 'MICROSOFT CORP',     70,  -0.30),
    ('426030', '2026-11-13', '30303M', 'META', 'META PLATFORMS INC', 47,  -0.06);
