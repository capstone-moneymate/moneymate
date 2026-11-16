-- "내 지도에 있어요" 통합 테스트용 (OverlapMyMapIntegrationTest). 마이그레이션(005 포함) 뒤에 실행된다.
-- 손계산: 사용자 1 이 배운 개념(total > 0)은 gpu_demand(2/3), rate_hike(1/1). semi_earnings 는 total 0 이라 안 배움.
--   gpu_demand -> AMD, NVDA / rate_hike 는 연결된 종목 없음 / semi_earnings -> NVDA 는 안 배워서 빠짐
--   => 종목: AMD [gpu_demand], NVDA [gpu_demand]. NVDA 상세: [gpu_demand]. GOOGL 상세: [] (ai_investment 안 배움)
-- 사용자 2 는 ai_investment(0/1)만 배움 (틀려도 푼 적 있으면 배운 개념) => GOOGL [ai_investment]
INSERT INTO concepts (id, name, theme, kind) VALUES
    ('ai_investment', 'AI 데이터센터 투자', 'AI·반도체', 'event'),
    ('gpu_demand', 'AI 반도체 수요', 'AI·반도체', 'indicator'),
    ('semi_earnings', '반도체 기업 실적', 'AI·반도체', 'outcome'),
    ('rate_hike', '기준금리 인상', '금리', 'event');

INSERT INTO users (id) VALUES
    ('11111111-1111-1111-1111-111111111111'),
    ('22222222-2222-2222-2222-222222222222');

INSERT INTO user_concepts (user_id, concept_id, correct, total) VALUES
    ('11111111-1111-1111-1111-111111111111', 'gpu_demand', 2, 3),
    ('11111111-1111-1111-1111-111111111111', 'semi_earnings', 0, 0),
    ('11111111-1111-1111-1111-111111111111', 'rate_hike', 1, 1),
    ('22222222-2222-2222-2222-222222222222', 'ai_investment', 0, 1);

INSERT INTO concept_tickers (concept_id, ticker, market, reason, source) VALUES
    ('gpu_demand', 'NVDA', 'US', 'GPU', 'https://www.sec.gov/a'),
    ('gpu_demand', 'AMD', 'US', 'GPU', 'https://www.sec.gov/b'),
    ('semi_earnings', 'NVDA', 'US', '반도체', 'https://www.sec.gov/a'),
    ('ai_investment', 'GOOGL', 'US', '설비투자', 'https://www.sec.gov/c');
