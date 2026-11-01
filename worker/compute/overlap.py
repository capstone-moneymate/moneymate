"""겹침 판정 (A). 큰손 13F 변화와 액티브 ETF 추세의 방향을 같은 시점 기준으로 비교해 overlap_results 에 저장한다.

실행 (worker/ 에서):
    python -m compute.overlap --period 2026-06-30          # 결과 요약 출력만
    python -m compute.overlap --period 2026-06-30 --save   # DB 에 저장 (calc_date = 오늘 KST)

규칙 (docs/conventions.md)
- P3: 큰손 방향과 ETF 방향이 같으면 same, 반대면 diff, 한쪽이 없거나 기준 미만이면 none
- P7: 13F 분기 말(period_end) 대비 ETF 최신 스냅샷만 비교한다. ETF 기준 스냅샷 = period_end 이후 첫 스냅샷
- P13: 13F new 는 늘림, exit 는 줄임. increase·decrease 는 INCREASE_THRESHOLD 이상 변했을 때만
- ETF 도 같은 방식: 기준일에 없다가 생기면 늘림, 기준일에 있다가 없어지면 줄임
- 13F 와 ETF 는 CUSIP 2~7번째 글자 = holdings_etf.raw_code 로 맞춘다 (findings.md B칸)
"""
import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import config
from common.quarters import parse_quarter_end

KST = timezone(timedelta(hours=9))
UP, DOWN = "up", "down"


def big_direction(change_type: str | None, chg_pct: float | None,
                  threshold: float = config.INCREASE_THRESHOLD) -> str | None:
    """13F 한 종목의 방향. up / down / None(판단 안 함)."""
    if change_type == "new":
        return UP
    if change_type == "exit":
        return DOWN
    if chg_pct is None:
        return None
    if chg_pct >= threshold:
        return UP
    if chg_pct <= -threshold:
        return DOWN
    return None


def etf_change(base_shares: Decimal | None, latest_shares: Decimal | None) -> tuple[str, float | None]:
    """ETF 기준일·최신 1CU 수량으로 (상태, 변화율). 상태: held / new / exit / none.
    변화율은 P2 와 같은 식이고 held 일 때만 있다."""
    has_base = base_shares is not None and base_shares > 0
    has_latest = latest_shares is not None and latest_shares > 0
    if has_base and has_latest:
        return "held", round(float((latest_shares - base_shares) / base_shares), 6)
    if has_latest:
        return "new", None
    if has_base:
        return "exit", -1.0
    return "none", None


def etf_direction(status: str, chg_pct: float | None,
                  threshold: float = config.ETF_TREND_THRESHOLD) -> str | None:
    if status == "new":
        return UP
    if status == "exit":
        return DOWN
    if status != "held" or chg_pct is None:
        return None
    if chg_pct >= threshold:
        return UP
    if chg_pct <= -threshold:
        return DOWN
    return None


def compare(big: str | None, etf: str | None) -> str:
    """두 방향을 same / diff / none 으로."""
    if big is None or etf is None:
        return "none"
    return "same" if big == etf else "diff"


def co_increased(big_dirs: dict[str, dict[str, str | None]], min_filers: int = 2) -> dict[str, list[str]]:
    """티커 -> {filer_key: 방향} 에서 min_filers 명 이상이 늘린 종목만. 탭 2 '함께 늘린 종목' 용.
    결과: 티커 -> 늘린 filer_key 목록(이름순)."""
    out = {}
    for ticker, dirs in big_dirs.items():
        ups = sorted(k for k, d in dirs.items() if d == UP)
        if len(ups) >= min_filers:
            out[ticker] = ups
    return out


# ------------------------------------------------------------------
# DB
# ------------------------------------------------------------------

def load_big(conn, period: date) -> list[dict]:
    """이번 분기 13F (큰손·CUSIP 단위로 한 줄). change_type 이 아직 없으면 holdings_change 를 먼저 돌려야 한다."""
    rows = conn.execute(
        """SELECT DISTINCT ON (filer_key, cusip) filer_key, cusip, ticker, change_type, chg_pct
           FROM holdings_13f WHERE period_end = %s
           ORDER BY filer_key, cusip, shares DESC""",
        (period,),
    ).fetchall()
    return [{"filer_key": f, "cusip": c, "ticker": t, "change_type": ct,
             "chg_pct": float(p) if p is not None else None} for f, c, t, ct, p in rows]


def load_etf(conn, period: date) -> dict[str, dict]:
    """ETF 별 기준·최신 스냅샷. etf_code -> {base_date, latest_date, base: {raw_code: shares}, latest: {...}}"""
    out = {}
    codes = [c for (c,) in conn.execute(
        "SELECT DISTINCT etf_code FROM holdings_etf WHERE snapshot_date >= %s", (period,)).fetchall()]
    for code in codes:
        base_date, latest_date = conn.execute(
            "SELECT min(snapshot_date), max(snapshot_date) FROM holdings_etf WHERE etf_code = %s AND snapshot_date >= %s",
            (code, period),
        ).fetchone()
        snap = {}
        for d in (base_date, latest_date):
            snap[d] = dict(conn.execute(
                "SELECT raw_code, shares FROM holdings_etf WHERE etf_code = %s AND snapshot_date = %s",
                (code, d),
            ).fetchall())
        out[code] = {"base_date": base_date, "latest_date": latest_date,
                     "base": snap[base_date], "latest": snap[latest_date]}
    return out


def build_results(big_rows: list[dict], etfs: dict[str, dict], period: date, calc_date: date) -> list[dict]:
    """겹침 행 목록. ETF 가 기준일이나 최신에 그 종목을 가진 (큰손, ETF) 쌍만 만든다. 티커 없는 13F 행은 뺀다."""
    results = []
    for b in big_rows:
        if not b["ticker"]:
            continue
        raw_code = b["cusip"][1:7]
        bdir = big_direction(b["change_type"], b["chg_pct"])
        for code, e in etfs.items():
            status, etf_pct = etf_change(e["base"].get(raw_code), e["latest"].get(raw_code))
            if status == "none":
                continue
            results.append({
                "calc_date": calc_date, "ticker": b["ticker"], "filer_key": b["filer_key"],
                "big_period_end": period, "big_chg_pct": b["chg_pct"],
                "etf_code": code, "etf_snapshot_date": e["latest_date"], "etf_trend_chg_pct": etf_pct,
                "direction": compare(bdir, etf_direction(status, etf_pct)),
            })
    return results


def save_results(conn, results: list[dict]) -> None:
    for r in results:
        conn.execute(
            """INSERT INTO overlap_results (calc_date, ticker, filer_key, big_period_end, big_chg_pct,
                   etf_code, etf_snapshot_date, etf_trend_chg_pct, direction)
               VALUES (%(calc_date)s, %(ticker)s, %(filer_key)s, %(big_period_end)s, %(big_chg_pct)s,
                   %(etf_code)s, %(etf_snapshot_date)s, %(etf_trend_chg_pct)s, %(direction)s)
               ON CONFLICT (calc_date, ticker, filer_key, etf_code) DO UPDATE SET
                   big_period_end = EXCLUDED.big_period_end, big_chg_pct = EXCLUDED.big_chg_pct,
                   etf_snapshot_date = EXCLUDED.etf_snapshot_date,
                   etf_trend_chg_pct = EXCLUDED.etf_trend_chg_pct, direction = EXCLUDED.direction""",
            r,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="큰손·ETF 겹침 판정")
    parser.add_argument("--period", required=True, help="13F 분기 말 (예: 2026-06-30)")
    parser.add_argument("--save", action="store_true", help="DB 에 저장")
    args = parser.parse_args(argv)
    period = parse_quarter_end(args.period)
    calc_date = datetime.now(KST).date()

    from db import get_conn
    with get_conn() as conn:
        big_rows = load_big(conn, period)
        if any(b["change_type"] is None for b in big_rows):
            print("change_type 이 비어 있는 13F 행이 있습니다. compute.holdings_change 를 먼저 --save 로 돌려 주세요.")
            return 1
        etfs = load_etf(conn, period)
        if not etfs:
            print(f"{period} 이후 ETF 스냅샷이 없습니다.")
            return 1
        for code, e in etfs.items():
            print(f"ETF {code}: 기준 {e['base_date']} → 최신 {e['latest_date']}"
                  + ("  (기준일이 분기 말과 다름)" if e["base_date"] != period else ""))
        results = build_results(big_rows, etfs, period, calc_date)
        counts = {}
        for r in results:
            counts[r["direction"]] = counts.get(r["direction"], 0) + 1
        print(f"겹침 {len(results)}쌍 {dict(sorted(counts.items()))}  (티커 없는 13F {sum(not b['ticker'] for b in big_rows)}행 제외)")
        if args.save:
            save_results(conn, results)
            print("DB 에 저장했습니다.")
        else:
            conn.rollback()
            print("출력만 했습니다. 저장하려면 --save 를 붙이세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
