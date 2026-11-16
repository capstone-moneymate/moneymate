"""13F 분기 갱신 점검 (A, #99). 수집·변화 계산을 마친 분기의 holdings_13f 를 읽어 이상한 값이 없는지 본다.

실행 (worker/ 에서):
    python scripts/check_13f_quarter.py --period 2026-09-30          # DB 만 읽는다
    python scripts/check_13f_quarter.py --period 2026-09-30 --raw    # SEC 원본도 받아 옵션·채권 제외를 확인

보는 것
1. 큰손 4명 모두 그 분기 행이 있는지 (없으면 공시 전이거나 수집 전)
2. 큰손별 보유 종목 수(exit 행 제외)와 직전 분기 대비 증감. 절반 이상 줄었거나 0이 되면 "급감"으로 표시
3. 변화 종류(change_type) 개수, change_type 이 비어 있는 행(holdings_change 를 안 돌림)
4. 변화율 상위·하위 5개 (chg_pct 가 NULL 인 new 는 빠진다. exit 는 -1 이라 하위에 나온다)
5. 제출 법인(CIK) 목록 — 같은 큰손의 여러 법인이 합쳐졌는지
6. 티커를 못 찾은 CUSIP 목록
7. (--raw) 원본 infotable 의 옵션(PutCall)·채권(PRN) 줄 수와 저장한 종목 수

판단·수정은 하지 않는다. 값이 이상하면 사람이 원인을 본다. 데이터를 고치지 않는다 (읽기 전용).
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

import config  # noqa: E402
from common.quarters import parse_quarter_end, prev_quarter_end  # noqa: E402

TOP_N = 5
# 직전 분기 대비 이만큼 이상 줄면 "급감"으로 표시 (점검 표시용, 늘림 임계값과 무관)
DROP_RATIO = 0.5


def drop_note(prev_n: int, curr_n: int, ratio: float = DROP_RATIO) -> str | None:
    """종목 수 변화가 이상하면 이유 문구, 아니면 None."""
    if prev_n > 0 and curr_n == 0:
        return "급감: 종목 0개 (빈 13F 이거나 수집 누락)"
    if prev_n > 0 and curr_n <= prev_n * (1 - ratio):
        return f"급감: {prev_n} → {curr_n} ({(curr_n - prev_n) / prev_n:+.0%})"
    return None


def top_bottom(rows: list[dict], n: int = TOP_N) -> tuple[list[dict], list[dict]]:
    """chg_pct 가 있는 행에서 상위 n, 하위 n. 같은 값은 티커(없으면 CUSIP) 순."""
    has = [r for r in rows if r["chg_pct"] is not None]
    key = lambda r: (r["ticker"] or r["cusip"])  # noqa: E731
    top = sorted(has, key=lambda r: (-r["chg_pct"], key(r)))[:n]
    bottom = sorted(has, key=lambda r: (r["chg_pct"], key(r)))[:n]
    return top, bottom


def raw_counts(infotable) -> dict[str, int]:
    """원본 infotable 줄 수. collectors.filings_13f.shares_by_cusip 와 같은 조건으로 센다."""
    put_call = infotable["PutCall"].fillna("").str.strip()
    return {
        "전체": len(infotable),
        "옵션(PUT/CALL)": int((put_call != "").sum()),
        "채권 등(Shares 아님)": int((infotable["Type"] != "Shares").sum()),
    }


# ------------------------------------------------------------------
# DB
# ------------------------------------------------------------------

def load_rows(conn, filer_key: str, period: date) -> list[dict]:
    """큰손·분기의 CUSIP 단위 행 (여러 법인은 합산, 변화 값은 holdings_change 가 큰손 단위로 적어 둔 값)."""
    rows = conn.execute(
        """SELECT cusip, max(ticker), max(issuer_name), sum(shares), max(chg_pct), max(change_type)
           FROM holdings_13f WHERE filer_key = %s AND period_end = %s GROUP BY cusip""",
        (filer_key, period),
    ).fetchall()
    return [{"cusip": c, "ticker": t, "issuer_name": i, "shares": int(s),
             "chg_pct": float(p) if p is not None else None, "change_type": ct}
            for c, t, i, s, p, ct in rows]


def held_count(rows: list[dict]) -> int:
    return sum(1 for r in rows if r["shares"] > 0)


def label(r: dict) -> str:
    name = (r["issuer_name"] or "")[:22]
    return f"{(r['ticker'] or '(티커없음)'):8s} {name:22s}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="13F 분기 갱신 점검")
    parser.add_argument("--period", required=True, help="분기 말 (예: 2026-09-30)")
    parser.add_argument("--raw", action="store_true", help="SEC 원본을 받아 옵션·채권 제외 확인")
    args = parser.parse_args(argv)
    period = parse_quarter_end(args.period)
    prev = prev_quarter_end(period)

    from db import get_conn
    with get_conn() as conn:
        missing = []
        print(f"== {period} 13F 점검 (직전 {prev})\n")
        for key in config.FILERS:
            curr_rows = load_rows(conn, key, period)
            prev_rows = load_rows(conn, key, prev)
            if not curr_rows:
                missing.append(key)
                print(f"[{key}] {period} 행 없음 — 공시 전이거나 수집 전\n")
                continue
            ciks = [c for (c,) in conn.execute(
                "SELECT DISTINCT filer_cik FROM holdings_13f WHERE filer_key = %s AND period_end = %s ORDER BY 1",
                (key, period)).fetchall()]
            filed = conn.execute(
                "SELECT min(filed_at), max(filed_at) FROM holdings_13f WHERE filer_key = %s AND period_end = %s",
                (key, period)).fetchone()
            n_now, n_prev = held_count(curr_rows), held_count(prev_rows)
            kinds: dict[str, int] = {}
            for r in curr_rows:
                kinds[r["change_type"] or "(비어 있음)"] = kinds.get(r["change_type"] or "(비어 있음)", 0) + 1
            exits = [r for r in curr_rows if r["change_type"] == "exit"]
            bad_exit = [r for r in exits if r["shares"] != 0 or r["chg_pct"] != -1.0]

            print(f"[{key}] 법인 {ciks}  공시일 {filed[0]}{'' if filed[0] == filed[1] else ' ~ ' + str(filed[1])}")
            print(f"  보유 종목 {n_now} (직전 {n_prev}, {n_now - n_prev:+d})"
                  + (f"  ← {drop_note(n_prev, n_now)}" if drop_note(n_prev, n_now) else ""))
            print(f"  변화 종류 {dict(sorted(kinds.items()))}")
            if "(비어 있음)" in kinds:
                print("  ! change_type 이 빈 행이 있음 → compute.holdings_change --save 를 먼저")
            if bad_exit:
                print(f"  ! exit 행 규칙(shares=0, chg_pct=-1) 위반 {len(bad_exit)}개")
            top, bottom = top_bottom(curr_rows)
            print("  상위 5")
            for r in top:
                print(f"    {label(r)} {r['chg_pct']:+.2%}  {r['change_type']}")
            print("  하위 5")
            for r in bottom:
                print(f"    {label(r)} {r['chg_pct']:+.2%}  {r['change_type']}")
            no_ticker = [r for r in curr_rows if not r["ticker"]]
            if no_ticker:
                print(f"  티커 못 찾음 {len(no_ticker)}개: " + ", ".join(
                    f"{r['cusip']}({(r['issuer_name'] or '')[:20]})" for r in no_ticker))
            print()

    if args.raw:
        print("== SEC 원본 확인 (옵션·채권은 저장하지 않아야 함)")
        from edgar import set_identity
        from collectors.filings_13f import fetch_reports, merge_reports
        set_identity(config.EDGAR_IDENTITY)
        for key, filer in config.FILERS.items():
            for cik in [filer["cik"], *filer.get("extra_ciks", [])]:
                reports = fetch_reports(cik, period)
                if not reports:
                    continue
                table, base = merge_reports(reports)
                counts = {}
                for r in reports:
                    for k, v in raw_counts(r.infotable).items():
                        counts[k] = counts.get(k, 0) + v
                print(f"  {key:14s} {cik}  원본 {counts}  → 저장 대상 {len(table)}종목 (신고 {len(reports)}건)")

    if missing:
        print(f"\n공시 전 또는 수집 전: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
