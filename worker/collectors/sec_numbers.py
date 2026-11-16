"""미국 8-K 실적 공시(Item 2.02)에 분기 실적 숫자 붙이기 (C). raw_sources.numbers 를 채운다.

8-K 는 제목(Item 2.02)만 저장해서 탭 2 이유가 "공시 내용은 알 수 없지만"이라고만 썼다 (2026-11-16 2분기 20종목).
보도자료(Exhibit 99.1) HTML 은 회사마다 표가 달라 읽기 어려워서, SEC 가 정해진 형식으로 주는 XBRL 재무 데이터
(data.sec.gov/api/xbrl/companyfacts)의 분기 매출·순이익·주당순이익을 쓰고 전년동기 대비 증감률은 코드가 계산한다.

- 어느 분기인가: 8-K 접수일보다 앞에 끝난 분기 중 가장 최근, 접수일과 75일 이내 (실적 발표는 분기 끝나고 한두 달 뒤)
- 분기 값: 기간이 80~100일인 값. 회계연도 4분기는 SEC 에 분기 값이 없고 연간(10-K)만 있어서 연간 − 9개월 누계로 계산한다
  (매출·순이익만. 주당순이익은 주식 수가 분기마다 달라 빼면 맞지 않아서 그 분기는 넣지 않는다)
- 전년동기: 그 분기 끝날의 1년 전(±10일)에 끝난 분기
- 키는 DART numbers 와 같은 말(매출액·당기순이익·전년동기대비(%)·방향). 금액은 백만달러, 주당순이익은 달러
- 값은 회사가 10-Q·10-K 로 낸 것이라 8-K 보도자료와 같은 숫자지만, 10-Q 접수는 8-K 와 같은 날이거나 며칠 뒤일 수 있다

실행 (worker/ 에서): python -m collectors.sec_numbers           # 저장 안 함, 채울 값만 출력
                     python -m collectors.sec_numbers --save    # numbers 가 빈 8-K 실적 공시를 채운다
필요: .env 의 EDGAR_IDENTITY (SEC 가 User-Agent 로 요구). edgartools 를 쓰지 않아 Windows 에서도 돈다.
"""
import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

import config  # noqa: E402  .env 를 읽는다
from collectors.dart_numbers import direction  # noqa: E402

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
MAX_LAG_DAYS = 75  # 분기 끝 → 8-K 실적 발표 사이 최대 일수
QUARTER_DAYS = (80, 100)
NINE_MONTH_DAYS = (260, 285)
YEAR_DAYS = (350, 380)

# 매출은 회사마다 쓰는 태그가 달라 앞에서부터 그 분기 값이 있는 것을 쓴다
ITEMS = [
    ("매출액", ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"], "USD", 1e6),
    ("당기순이익", ["NetIncomeLoss"], "USD", 1e6),
    ("주당순이익(희석)", ["EarningsPerShareDiluted"], "USD/shares", 1),
]


@dataclass
class Period:
    start: date
    end: date
    val: float
    derived: bool = False  # 연간 − 9개월 누계로 만든 회계연도 4분기


def _days(p: dict) -> int:
    return (date.fromisoformat(p["end"]) - date.fromisoformat(p["start"])).days


def _latest_by_span(rows: list[dict], lo: int, hi: int) -> dict[tuple[date, date], float]:
    """기간 길이가 lo~hi 일인 값을 (시작, 끝)마다 하나씩 (가장 늦게 접수된 값, 정정 반영)."""
    out: dict[tuple[date, date], tuple[str, float]] = {}
    for r in rows:
        if "start" not in r or r.get("form") not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
            continue
        if not lo <= _days(r) <= hi:
            continue
        key = (date.fromisoformat(r["start"]), date.fromisoformat(r["end"]))
        if key not in out or r["filed"] > out[key][0]:
            out[key] = (r["filed"], float(r["val"]))
    return {k: v for k, (_, v) in out.items()}


def quarters(rows: list[dict]) -> dict[date, Period]:
    """끝날 → 분기 값. 분기 값이 없는 회계연도 4분기는 연간 − 같은 시작일의 9개월 누계로 만든다."""
    out = {end: Period(start, end, v) for (start, end), v in _latest_by_span(rows, *QUARTER_DAYS).items()}
    nine = _latest_by_span(rows, *NINE_MONTH_DAYS)
    for (ys, ye), yv in _latest_by_span(rows, *YEAR_DAYS).items():
        if ye in out:
            continue
        for (ns, ne), nv in nine.items():
            if ns == ys and 80 <= (ye - ne).days <= 100:
                out[ye] = Period(ne + timedelta(days=1), ye, yv - nv, derived=True)
    return out


def pick_quarter(qs: dict[date, Period], filed: date) -> Period | None:
    ends = [e for e in qs if e < filed and (filed - e).days <= MAX_LAG_DAYS]
    return qs[max(ends)] if ends else None


def year_ago(qs: dict[date, Period], end: date) -> Period | None:
    target = end - timedelta(days=365)
    near = [e for e in qs if abs((e - target).days) <= 10]
    return qs[min(near, key=lambda e: abs((e - target).days))] if near else None


def turn(prev: float, cur: float) -> str | None:
    """부호가 바뀌면 흑자전환·적자전환, 둘 다 음수면 적자지속 (DART 흑자적자전환 칸과 같은 말)."""
    if prev < 0 <= cur:
        return "흑자전환"
    if prev >= 0 > cur:
        return "적자전환"
    if prev < 0 and cur < 0:
        return "적자지속"
    return None


def earnings_numbers(facts: dict, filed: date) -> dict:
    """companyfacts JSON 과 8-K 접수일 → numbers. 그 분기 값을 못 찾으면 빈 dict."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    out: dict = {}
    period = None
    for label, tags, unit, scale in ITEMS:
        for tag in tags:
            rows = gaap.get(tag, {}).get("units", {}).get(unit)
            if not rows:
                continue
            qs = quarters(rows)
            cur = pick_quarter(qs, filed) if period is None else qs.get(period.end)
            if cur is None:
                continue
            period = period or cur
            money = scale != 1
            prev = year_ago(qs, cur.end)
            # 주당순이익은 분기마다 주식 수가 달라 연간 − 9개월로 빼면 맞지 않는다 (MSFT 17.95 − 13.14 = 4.81 은 근삿값)
            if not money and (cur.derived or (prev and prev.derived)):
                if cur.derived:
                    break
                prev = None
            fmt = (lambda v: round(v / scale)) if money else (lambda v: round(v, 2))
            out[label] = fmt(cur.val)
            if prev is not None:
                out[f"{label} 전년동기"] = fmt(prev.val)
                t = turn(prev.val, cur.val)
                pct = None if t or prev.val == 0 else round((cur.val / prev.val - 1) * 100, 1)
                if pct is not None:
                    out[f"{label} 전년동기대비(%)"] = pct
                d = direction(pct, t)
                if d:
                    out[f"{label} 전년동기대비 방향"] = d
            break
    if period is None:
        return {}
    return {"실적기간": f"{period.start}~{period.end}", "단위": "백만달러 (주당순이익은 달러)", **out}


# ------------------------------------------------------------------
# SEC 호출
# ------------------------------------------------------------------
def _headers() -> dict:
    if not config.EDGAR_IDENTITY:
        raise RuntimeError("EDGAR_IDENTITY 가 비어 있습니다 (.env, 영문 이름 + 이메일)")
    return {"User-Agent": config.EDGAR_IDENTITY}


def load_ciks() -> dict[str, int]:
    """티커 → CIK. SEC company_tickers.json 의 '.' 는 우리 형식(P1, BRK-B)의 '-' 로 맞춘다."""
    data = requests.get(TICKERS_URL, headers=_headers(), timeout=30).json()
    return {v["ticker"].upper().replace(".", "-"): int(v["cik_str"]) for v in data.values()}


def fetch_facts(cik: int) -> dict:
    res = requests.get(FACTS_URL.format(cik=cik), headers=_headers(), timeout=60)
    res.raise_for_status()
    return res.json()


def fill(conn, rows: list[tuple[int, str, date]], ciks: dict[str, int], save: bool) -> int:
    """rows: (raw_sources.id, 티커, 발표일). 티커마다 companyfacts 를 한 번만 받는다. 채운 줄 수."""
    facts_cache: dict[str, dict | None] = {}
    filled = 0
    for sid, ticker, published in rows:
        if ticker not in facts_cache:
            cik = ciks.get(ticker)
            try:
                facts_cache[ticker] = fetch_facts(cik) if cik else None
            except requests.RequestException as e:
                print(f"경고: {ticker} companyfacts 를 못 받았어요 ({e.__class__.__name__})", file=sys.stderr)
                facts_cache[ticker] = None
        facts = facts_cache[ticker]
        nums = earnings_numbers(facts, published) if facts else {}
        print(f"{ticker:6} {published} {json.dumps(nums, ensure_ascii=False) if nums else '(못 찾음)'}")
        if nums and save:
            conn.execute("UPDATE raw_sources SET numbers = numbers || %s::jsonb WHERE id = %s",
                         (json.dumps(nums, ensure_ascii=False), sid))
        filled += bool(nums)
    return filled


def main(argv: list[str] | None = None) -> int:
    from db import get_conn

    parser = argparse.ArgumentParser(description="미국 8-K 실적 공시에 분기 실적 숫자 붙이기")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--all", action="store_true", help="이미 숫자가 있는 공시도 다시 계산")
    args = parser.parse_args(argv)
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, ticker, published_date FROM raw_sources
               WHERE source_type = 'sec_8k' AND category = 'earnings' AND ticker IS NOT NULL
                 AND (%s OR numbers = '{}'::jsonb)
               ORDER BY ticker, published_date""",
            (args.all,),
        ).fetchall()
        n = fill(conn, rows, load_ciks(), args.save)
        if args.save:
            conn.commit()
    print(f"\n실적 숫자 {n}/{len(rows)}건{' 저장' if args.save else ' (저장 안 함, --save)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
