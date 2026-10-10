-- 머니메이트 002_13f_etf_fixes.sql  (작성: A)
-- 001_init.sql 검토 후 보완. 규칙은 docs/conventions.md P12~P15 참고.
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/002_13f_etf_fixes.sql

BEGIN;

-- ============================================================
-- holdings_13f: 변화 종류 (A 담당)
-- ============================================================
-- holdings_change.py 가 prev_shares, chg_pct 와 함께 채운다. 채우기 전에는 NULL.
-- new: 직전 분기에 없음 / exit: 이번 분기 shares=0 (전량 매도) / increase·decrease·unchanged: 수량 비교
ALTER TABLE holdings_13f
    ADD COLUMN change_type TEXT
    CHECK (change_type IN ('new', 'increase', 'decrease', 'exit', 'unchanged'));

-- ============================================================
-- holdings_etf: 추세 기준일 (B 담당)
-- ============================================================
-- trend_chg_pct, trend_adj_pct 를 계산할 때 비교한 스냅샷 날짜.
-- 보통 13F 분기 말(예: 2026-09-30), 그날 스냅샷이 없으면 수집 시작일.
ALTER TABLE holdings_etf
    ADD COLUMN trend_base_date DATE;

COMMIT;
