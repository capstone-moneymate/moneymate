-- 머니메이트 007_price_sources.sql  (초안: C, A 확인 필요)
-- raw_sources 에 가격 자료(source_type = 'price')를 허용한다.
-- 1차 자료(공시·발표)가 아니라 코드가 가격표에서 계산한 움직임이다. 4주차 A4 제안(가격 카드 출처 형식)과 같은 모양이다.
--   차트 종목 카드 (worker/generate/stock_move_card.py, #191, docs/modules/stock_move_card.md)
--     source_type = 'price', category = 'stock_move', market = 'KR', ticker = 국내 6자리
--     source_key  = '{종목코드}_stock_move_{YYYY-MM-DD}' (예: 035900_stock_move_2026-11-18)
--     numbers     = 종가·등락률·거래량·평소 대비 거래량 배수·선별 점수·같은 날 자료 제목
-- 선별(run_daily.load_sources)과 같은 날 자료 찾기는 source_type <> 'price' 로 이 자료를 뺀다.
-- 번호 007 은 #191 때 올렸어야 했는데 빠졌던 것이다. 새 DB는 006 다음에 자동 적용된다.
-- 이미 만든 DB에 적용 (손으로 바꿔 둔 DB에 다시 돌려도 된다):
--   docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/007_price_sources.sql

BEGIN;

ALTER TABLE raw_sources DROP CONSTRAINT IF EXISTS raw_sources_source_type_check;
ALTER TABLE raw_sources ADD CONSTRAINT raw_sources_source_type_check
    CHECK (source_type IN ('dart', 'sec_8k', 'macro', 'price'));

COMMIT;
