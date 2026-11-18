"""탭 2 카드 ②③ 분기 생성 (C). 13F 분기 갱신(docs/modules/check_13f_quarter.md 1~4단계) 뒤에 한 번 돌린다.

사용 예 (worker 폴더에서):
    python -m scripts.run_reasons --period 2026-09-30 --no-llm     # 종목·방향·근거 수만 보기 (비용 0, 저장 안 함)
    python -m scripts.run_reasons --period 2026-09-30 --ticker NVDA # 한 종목만 (Sonnet + Haiku, 저장)
    python -m scripts.run_reasons --period 2026-09-30               # 겹침 결과의 모든 종목

종목마다: overlap_results(가장 최근 calc_date) → stock_direction(방향·change, P19) → 카드 ① 숫자 문장(코드)
→ load_evidence(기준일 이전 자료) → reasons.generate(Sonnet, 근거가 없으면 호출 안 함)
→ stock_now.generate(카드 ③, Haiku. 이유가 있을 때만) → reasons.save (published / rejected).
카드 ③은 날마다 바뀌어서 run_daily 의 "지금은 갱신" 단계가 now_view 만 다시 만든다.
"""
import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

# 화면(web/src/pages/tab2/labels.ts)과 같은 이름. 카드 ① 숫자 문장을 이유 프롬프트에 넣을 때 쓴다
FILER_PERSON = {"buffett": "버핏의 회사", "druckenmiller": "드러켄밀러의 회사", "thiel": "틸의 회사",
                "ackman": "애크먼의 회사"}
ETF_SHORT = {"426030": "TIME", "0015B0": "KoAct"}


@dataclass
class StockRun:
    ticker: str
    direction: str | None = None
    change: str | None = None
    evidence: int = 0
    status: str | None = None  # published / rejected / None(저장 안 함)
    calls: int = 0
    error: str | None = None
    warnings: int = 0  # 다시 써도 방향이 큰손 변화와 반대라 뺀 이유 수 (reasons.direction_warnings)


def pct_text(v: float | None) -> str | None:
    """P2 비율 → '+24%' / '-16.3%'. 정수면 소수점 없이."""
    if v is None:
        return None
    p = round(float(v) * 100, 1)
    return f"{'+' if p > 0 else ''}{int(p) if p == int(p) else p}%"


def big_text(change_type: str | None, chg_pct: float | None) -> str | None:
    if change_type == "new":
        return "새로 담음"
    if change_type == "exit":
        return "모두 정리"
    return pct_text(chg_pct)


def facts_for(rows: list[dict], base_date: date) -> list[str]:
    """카드 ① 숫자 문장 (코드가 만든다. 이유 프롬프트의 <facts>). 큰손은 한 번씩, ETF 도 한 번씩."""
    facts, seen_f, seen_e = [], set(), set()
    for r in rows:
        if r["filer_key"] not in seen_f:
            seen_f.add(r["filer_key"])
            t = big_text(r.get("change_type"), r.get("big_chg_pct"))
            if t:
                facts.append(f"{FILER_PERSON.get(r['filer_key'], r['filer_key'])} {base_date:%m/%d} 기준 {t}")
        if r["etf_code"] not in seen_e:
            seen_e.add(r["etf_code"])
            t = pct_text(r.get("etf_trend_chg_pct"))
            if t:
                facts.append(f"{ETF_SHORT.get(r['etf_code'], r['etf_code'])} {base_date:%m/%d} 대비 {t}")
    return facts


def load_overlap(conn, period: date, ticker: str | None = None) -> dict[str, list[dict]]:
    """그 분기의 가장 최근 calc_date 겹침 줄을 종목별로. change_type·종목명은 holdings_13f 에서 붙인다."""
    rows = conn.execute(
        """WITH last AS (SELECT max(calc_date) AS d FROM overlap_results WHERE big_period_end = %s)
           SELECT o.ticker, o.filer_key, o.big_chg_pct, o.etf_code, o.etf_trend_chg_pct, o.direction,
                  h.change_type, h.issuer_name
             FROM overlap_results o JOIN last ON o.calc_date = last.d
             LEFT JOIN LATERAL (
                 SELECT change_type, issuer_name FROM holdings_13f
                  WHERE period_end = o.big_period_end AND filer_key = o.filer_key AND ticker = o.ticker
                  ORDER BY shares DESC LIMIT 1) h ON true
            WHERE o.big_period_end = %s AND (%s::text IS NULL OR o.ticker = %s)
            ORDER BY o.ticker, o.filer_key, o.etf_code""",
        (period, period, ticker, ticker),
    ).fetchall()
    cols = ["ticker", "filer_key", "big_chg_pct", "etf_code", "etf_trend_chg_pct", "direction",
            "change_type", "issuer_name"]
    out: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        d = dict(zip(cols, r))
        for k in ("big_chg_pct", "etf_trend_chg_pct"):
            d[k] = float(d[k]) if d[k] is not None else None
        out[d["ticker"]].append(d)
    return dict(out)


def fill_prices(conn, ticker: str, period: date, today: date | None = None) -> int:
    """카드 ③ 주가용 미국 종목 종가를 기준일 10일 전부터 오늘까지 받는다 (run_daily 갱신 단계와 같은 범위)."""
    from datetime import timedelta

    from collectors.prices import fetch_us, save_prices

    n = save_prices(conn, fetch_us(ticker, period - timedelta(days=10), today or date.today()))
    conn.commit()
    return n


def run_one(conn, ticker: str, rows: list[dict], period: date, llm: bool) -> StockRun:
    from generate import reasons, stock_now

    run = StockRun(ticker)
    try:
        run.direction, run.change = reasons.stock_direction(rows)
    except ValueError as e:
        run.error = str(e)
        return run
    evidence = reasons.load_evidence(ticker, period)
    run.evidence = len(evidence)
    if not llm:
        return run
    stock = {"ticker": ticker, "name": rows[0].get("issuer_name")}
    result = reasons.generate(stock, run.direction, run.change, period, facts_for(rows, period), evidence)
    run.calls = result.calls
    run.warnings = len(result.warnings)
    now_view = None
    if result.reasons:
        try:
            fill_prices(conn, ticker, period)
        except Exception as e:  # noqa: BLE001  가격을 못 받아도 카드 ③은 자료·연결로 만든다 (price=null)
            print(f"  {ticker} 가격을 받지 못했어요: {e.__class__.__name__}: {str(e)[:80]}")
        now = stock_now.generate(stock, period, result.reasons)
        run.calls += now.calls
        now_view = now.to_json()
    run.status = reasons.save(conn, period, ticker, run.direction, run.change, result, now_view,
                              {"model": "reasons=sonnet, now=haiku"})
    conn.commit()  # 종목마다 저장 (중간에 멈춰도 앞 종목은 남는다)
    return run


def main(argv: list[str] | None = None) -> int:
    from db import get_conn

    parser = argparse.ArgumentParser(description="탭 2 카드 ②③ 분기 생성")
    parser.add_argument("--period", required=True, help="13F 분기 말 YYYY-MM-DD")
    parser.add_argument("--ticker", help="한 종목만")
    parser.add_argument("--no-llm", action="store_true", help="방향·근거 수만 보기 (비용 0, 저장 안 함)")
    args = parser.parse_args(argv)
    period = date.fromisoformat(args.period)

    with get_conn() as conn:
        by_ticker = load_overlap(conn, period, args.ticker)
        if not by_ticker:
            print(f"{period} 겹침 결과가 없어요 (compute.overlap --period {period} --save 먼저)")
            return 1
        runs = []
        for ticker, rows in by_ticker.items():
            run = run_one(conn, ticker, rows, period, llm=not args.no_llm)
            runs.append(run)
            print(f"{ticker:8} {run.direction or '-':5} {run.change or '-':5} 근거 {run.evidence:2}건 "
                  f"{run.status or ('건너뜀' if run.error else '-')} 호출 {run.calls} 방향 뺌 {run.warnings} {run.error or ''}")
    done = [r for r in runs if r.status == "published"]
    print(f"\n종목 {len(runs)}개, published {len(done)}, "
          f"rejected {sum(r.status == 'rejected' for r in runs)}, "
          f"방향 못 정함 {sum(bool(r.error) for r in runs)}, 방향 반대로 뺀 이유 {sum(r.warnings for r in runs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
