"""큰손 변화 계산 (A). holdings_13f 의 직전 분기 대비 prev_shares·chg_pct·change_type 을 채운다.

실행 (worker/ 에서):
    python -m compute.holdings_change --period 2026-06-30          # 결과 요약 출력만
    python -m compute.holdings_change --period 2026-06-30 --save   # DB 에 반영

규칙 (docs/conventions.md)
- P2: chg_pct = (이번 - 직전) / 직전. 직전이 없거나 0이면 NULL
- P12: 직전 분기에 있었는데 이번 분기에 없으면 shares=0, chg_pct=-1, change_type='exit' 행을 만든다
- P13: change_type 은 수량 비교만으로 정한다 (임계값과 무관). 임계값은 겹침 판정(overlap.py)에서 쓴다
- 같은 큰손의 여러 법인(config.FILERS 의 extra_ciks)은 CUSIP 별로 합쳐서 비교한다
"""
import argparse
import sys
from dataclasses import dataclass
from datetime import date

import config
from common.quarters import parse_quarter_end, prev_quarter_end


@dataclass(frozen=True)
class Change:
    shares: int
    prev_shares: int | None
    chg_pct: float | None
    change_type: str  # new / increase / decrease / unchanged / exit


def classify_changes(curr: dict[str, int], prev: dict[str, int]) -> dict[str, Change]:
    """CUSIP -> 수량 두 분기를 비교한다. 수량이 0 이하인 CUSIP 은 '보유 안 함'으로 본다.

    이번 분기에 없거나 0이고 직전 분기에 있었으면 exit 를 만든다.
    """
    held_now = {c: s for c, s in curr.items() if s > 0}
    held_prev = {c: s for c, s in prev.items() if s > 0}
    result: dict[str, Change] = {}
    for c, s in held_now.items():
        p = held_prev.get(c)
        if p is None:
            result[c] = Change(s, None, None, "new")
            continue
        kind = "increase" if s > p else "decrease" if s < p else "unchanged"
        result[c] = Change(s, p, round((s - p) / p, 6), kind)
    for c, p in held_prev.items():
        if c not in held_now:
            result[c] = Change(0, p, -1.0, "exit")
    return result


# ------------------------------------------------------------------
# DB
# ------------------------------------------------------------------

def load_shares(conn, filer_key: str, period: date) -> dict[str, int]:
    """한 큰손·한 분기의 CUSIP 별 수량 (여러 법인 합산)."""
    rows = conn.execute(
        """SELECT cusip, sum(shares) FROM holdings_13f
           WHERE filer_key = %s AND period_end = %s GROUP BY cusip""",
        (filer_key, period),
    ).fetchall()
    return {c: int(s) for c, s in rows}


def apply_changes(conn, filer_key: str, period: date) -> dict[str, int] | None:
    """한 큰손의 변화를 DB 에 반영하고 종류별 개수를 돌려준다. 이번 분기 행이 없으면(공시 전) None.

    직전 분기 행이 없으면 전부 new 가 된다. 직전 분기에 보유가 없다고 낸 경우(틸 2026-03-31분)는 이게 맞지만,
    직전 분기를 수집하지 않은 경우는 틀리므로 main 이 경고한다. 수집기는 항상 두 분기를 함께 받는다.
    """
    prev_period = prev_quarter_end(period)
    curr = load_shares(conn, filer_key, period)
    prev = load_shares(conn, filer_key, prev_period)
    if not curr:
        return None

    changes = classify_changes(curr, prev)
    filer = config.FILERS[filer_key]
    head = conn.execute(
        """SELECT filed_at, accession_no FROM holdings_13f
           WHERE filer_key = %s AND period_end = %s AND filer_cik = %s AND shares > 0 LIMIT 1""",
        (filer_key, period, filer["cik"]),
    ).fetchone() or conn.execute(
        """SELECT filed_at, accession_no FROM holdings_13f
           WHERE filer_key = %s AND period_end = %s AND shares > 0 ORDER BY filed_at DESC LIMIT 1""",
        (filer_key, period),
    ).fetchone()

    counts: dict[str, int] = {}
    for cusip, ch in changes.items():
        counts[ch.change_type] = counts.get(ch.change_type, 0) + 1
        if ch.change_type == "exit":
            # 직전 분기 행에서 이름·티커를 가져와 이번 분기 행을 만든다 (대표 법인 CIK 로)
            info = conn.execute(
                """SELECT ticker, issuer_name FROM holdings_13f
                   WHERE filer_key = %s AND period_end = %s AND cusip = %s LIMIT 1""",
                (filer_key, prev_period, cusip),
            ).fetchone()
            conn.execute(
                """INSERT INTO holdings_13f (filer_key, filer_cik, filer_name, period_end, filed_at, accession_no,
                       cusip, ticker, issuer_name, shares, prev_shares, chg_pct, change_type)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, -1, 'exit')
                   ON CONFLICT (filer_cik, period_end, cusip) DO UPDATE SET
                       shares = 0, prev_shares = EXCLUDED.prev_shares, chg_pct = -1, change_type = 'exit'""",
                (filer_key, filer["cik"], filer["name"], period, head[0], head[1],
                 cusip, info[0], info[1], ch.prev_shares),
            )
        else:
            # 같은 CUSIP 을 여러 법인이 냈으면 모든 행에 큰손 단위 값을 적는다
            conn.execute(
                """UPDATE holdings_13f SET prev_shares = %s, chg_pct = %s, change_type = %s
                   WHERE filer_key = %s AND period_end = %s AND cusip = %s""",
                (ch.prev_shares, ch.chg_pct, ch.change_type, filer_key, period, cusip),
            )
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="13F 직전 분기 대비 변화 계산")
    parser.add_argument("--period", required=True, help="분기 말 (예: 2026-06-30)")
    parser.add_argument("--save", action="store_true", help="DB 에 반영 (없으면 계산 후 되돌림)")
    args = parser.parse_args(argv)
    period = parse_quarter_end(args.period)

    from db import get_conn
    conn = get_conn()
    try:
        for key in config.FILERS:
            counts = apply_changes(conn, key, period)
            if counts is None:
                print(f"{key:14s} 건너뜀: {period} 13F 가 DB 에 없음 (공시 전이거나 수집 전)")
                continue
            print(f"{key:14s} {dict(sorted(counts.items()))}")
            if set(counts) == {"new"}:
                print(f"{'':14s} 경고: {prev_quarter_end(period)} 행이 없어 전부 new. "
                      "그 분기에 보유가 없었는지(빈 13F) 확인하세요. 수집을 안 했다면 collectors.filings_13f 를 먼저")
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
