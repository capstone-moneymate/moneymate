"""ETF 추세·전일 대비 변화 (B). holdings_etf 의 trend_chg_pct·day_chg_pct·trend_base_date 를 채운다.

실행 (worker/ 에서):
    python -m compute.etf_trend                       # 모든 스냅샷 날짜 계산, 최신 날짜 요약 출력만
    python -m compute.etf_trend --date 2026-10-30     # 그날만
    python -m compute.etf_trend --save                # DB 에 반영

규칙 (docs/conventions.md)
- P2: 변화율 = (지금 - 이전) / 이전. 이전이 없거나 0이면 NULL (신규 편입)
      단, 그 ETF 의 첫 스냅샷 날은 전일이 없어 day_chg_pct 가 전 종목 NULL 이다 (신규가 아니라 비교 대상 없음)
- P15: 추세 기준일 = 그 스냅샷이 속한 분기의 분기 말. 그날 스냅샷이 없으면 그 이후 첫 스냅샷(수집 시작일).
       A의 overlap.py 가 ETF 기준 스냅샷을 고르는 방식과 같다
- P6: 스냅샷 수량·코드는 건드리지 않고 계산 컬럼만 채운다
- 1CU 기준 수량이라 자금 유입 보정은 하지 않는다 (findings.md B칸)

화면 표시용 값이다. 겹침 판정은 overlap.py 가 13F 분기 말 기준으로 따로 계산한다 (overlap.md).
"""
import argparse
import sys
from datetime import date
from decimal import Decimal

import config
from common.quarters import latest_quarter_end


def chg_pct(now: Decimal | None, prev: Decimal | None) -> float | None:
    """P2 변화율. overlap.etf_change 와 같은 식·같은 반올림(소수 6자리)."""
    if now is None or prev is None or prev <= 0:
        return None
    return round(float((now - prev) / prev), 6)


def trend_base_date(snapshot: date, dates: list[date]) -> date | None:
    """snapshot 의 추세 기준일 (P15). dates 는 그 ETF 의 스냅샷 날짜 전체.

    분기 말 당일 스냅샷이면 자기 자신이 기준이라 추세는 0이다. 분기 말 이후 수집을 시작했으면 첫 스냅샷이 기준이다.
    """
    q = latest_quarter_end(snapshot)
    after = [d for d in dates if q <= d <= snapshot]
    return min(after) if after else None


def previous_date(snapshot: date, dates: list[date]) -> date | None:
    """바로 앞 스냅샷 날짜 (전일 대비용). 수집을 빠뜨린 날이 있으면 그 앞 날짜가 된다."""
    before = [d for d in dates if d < snapshot]
    return max(before) if before else None


def compute_changes(curr: dict[str, Decimal], base: dict[str, Decimal],
                    prev: dict[str, Decimal]) -> dict[str, tuple[float | None, float | None]]:
    """raw_code -> (trend_chg_pct, day_chg_pct). curr 에 있는 종목만 (편출 종목은 그날 행이 없다)."""
    return {code: (chg_pct(s, base.get(code)), chg_pct(s, prev.get(code))) for code, s in curr.items()}


def summarize(changes: dict[str, tuple[float | None, float | None]],
              threshold: float = config.ETF_TREND_THRESHOLD) -> dict[str, int]:
    """추세 기준 개수 요약 (출력용). 늘림·줄임은 overlap 과 같은 임계값을 쓴다."""
    out = {"늘림": 0, "줄임": 0, "변화 작음": 0, "신규": 0}
    for trend, _ in changes.values():
        if trend is None:
            out["신규"] += 1
        elif trend >= threshold:
            out["늘림"] += 1
        elif trend <= -threshold:
            out["줄임"] += 1
        else:
            out["변화 작음"] += 1
    return out


# ------------------------------------------------------------------
# DB
# ------------------------------------------------------------------

def load_dates(conn, etf_code: str) -> list[date]:
    rows = conn.execute(
        "SELECT DISTINCT snapshot_date FROM holdings_etf WHERE etf_code = %s ORDER BY 1", (etf_code,)
    ).fetchall()
    return [d for (d,) in rows]


def load_snapshot(conn, etf_code: str, d: date | None) -> dict[str, Decimal]:
    if d is None:
        return {}
    rows = conn.execute(
        "SELECT raw_code, shares FROM holdings_etf WHERE etf_code = %s AND snapshot_date = %s", (etf_code, d)
    ).fetchall()
    return dict(rows)


def apply_day(conn, etf_code: str, snapshot: date, dates: list[date]):
    """한 ETF·한 날짜를 계산해 반영한다. (기준일, 직전일, 변화) 를 돌려준다."""
    base_date = trend_base_date(snapshot, dates)
    prev_date = previous_date(snapshot, dates)
    changes = compute_changes(load_snapshot(conn, etf_code, snapshot),
                              load_snapshot(conn, etf_code, base_date),
                              load_snapshot(conn, etf_code, prev_date))
    with conn.cursor() as cur:
        for code, (trend, day) in changes.items():
            cur.execute(
                """UPDATE holdings_etf SET trend_chg_pct = %s, day_chg_pct = %s, trend_base_date = %s
                   WHERE etf_code = %s AND snapshot_date = %s AND raw_code = %s""",
                (trend, day, base_date, etf_code, snapshot, code),
            )
    return base_date, prev_date, changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ETF 추세·전일 대비 변화 계산")
    parser.add_argument("--date", help="이 스냅샷 날짜만 (예: 2026-10-30). 없으면 모든 날짜")
    parser.add_argument("--save", action="store_true", help="DB 에 반영 (없으면 계산 후 되돌림)")
    args = parser.parse_args(argv)
    only = date.fromisoformat(args.date) if args.date else None

    from collectors.etf_holdings import ETFS
    from db import get_conn
    conn = get_conn()
    try:
        for code, name in ETFS.items():
            dates = load_dates(conn, code)
            targets = [only] if only else dates
            if not dates or (only and only not in dates):
                print(f"[{code}] 건너뜀: 스냅샷이 없음 (collectors/etf_holdings.py 를 먼저)")
                continue
            for d in targets:
                base_date, prev_date, changes = apply_day(conn, code, d, dates)
            print(f"[{code}] {name}: {len(targets)}일 계산. 최신 {d} (추세 기준 {base_date}, 전일 {prev_date or '없음'})")
            print(f"{'':9s}{summarize(changes)}")
        if args.save:
            conn.commit()
            print("\nDB 에 반영했습니다.")
        else:
            conn.rollback()
            print("\n출력만 했습니다. 반영하려면 --save 를 붙이세요.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
