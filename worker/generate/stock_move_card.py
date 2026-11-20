"""차트 종목 카드 (C). 탭 1 홈 종목 차트가 매일 하나는 나오게 하는 규칙.

규칙 (팀 결정 2026-11-20, 탭 1 차트용):
- 하루 카드 중 최소 1장은 차트를 그릴 수 있는 종목 카드(국내·미국 종목 ticker 가 있는 자료)여야 한다.
- 종목 카드가 있으면 그중 선별 점수 1위 종목을 차트로 보여 준다 (chart_candidate).
- 금리 발표처럼 종목 없는 거시 뉴스만 고른 날은 점수가 가장 낮은 카드를 빼고,
  그날 시장 반응(거래량·수익률 점수)이 가장 컸던 국내 종목(시가총액 1조 원 이상 중)의 주가·거래량 움직임으로 만든 카드를 넣는다
  (with_stock_card, top_reactor). 고른 카드가 3장보다 적으면 빼지 않고 더한다.
그래서 차트는 항상 하나 나오고, 차트를 누르면 그 카드뉴스로 이어진다.
어느 카드가 차트 카드인지는 cards.model_info.select.chart = true 로 남긴다 (서버가 읽는다).

움직임 카드 자료는 raw_sources 한 줄(source_type 'price', category 'stock_move')로 저장하고 compose 로 만든다.
유형은 코드가 1로 정한다. 숫자(종가·등락률·거래량 배수)는 모두 코드가 계산하고, 같은 날 그 종목 자료는
사실로만 넘긴다 (원인 단정 금지, 프롬프트 "오늘의 종목 움직임 카드" 규칙, CLAUDE.md 10).

사용 예 (worker/ 에서):
    python -m generate.stock_move_card 2026-11-17 --no-llm   # 그날 반응 1위 종목과 자료만 출력 (비용 0)
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from compute.source_select import Candidate, rank_key

KST = ZoneInfo("Asia/Seoul")
MARKET_CLOSE = time(15, 30)
CATEGORY = "stock_move"
VOLUME_LOOKBACK = 20  # 평소 거래량 = 직전 20거래일 평균
MAX_SAME_DAY = 3
STOCK_MARKETS = ("KR", "US")
# 반응 1위 후보의 시가총액 하한 (원). 소형주 급등락(예: 11/18 오리콤 -16.88%)이 홈 차트가 되지 않게 (C 결정 2026-11-21).
# 넘는 종목이 하나도 없거나 시가총액을 못 받으면 하한 없이 고른다 (차트는 항상 하나 나와야 한다).
MIN_MARKET_CAP = 1_000_000_000_000


# ------------------------------------------------------------------
# 1. 순수 규칙 (DB·네트워크 없음, tests/test_stock_move_card.py)
# ------------------------------------------------------------------

def is_common(ticker: str) -> bool:
    """보통주인가. 국내 코드는 보통주 끝자리가 0 이고 우선주는 5·7·9·K 등이다."""
    return ticker.endswith("0")


def direction_word(ratio: float) -> str:
    return "상승" if ratio > 0 else ("하락" if ratio < 0 else "보합")



def is_stock_source(src: dict | None) -> bool:
    """차트를 그릴 수 있는 종목 자료인가: 국내·미국 종목 ticker 가 있다. 지수(INDEX)·거시(macro)는 아니다."""
    return bool(src and src.get("ticker") and src.get("market") in STOCK_MARKETS)


def is_stock_candidate(c: Candidate) -> bool:
    return is_stock_source(c.extra.get("source"))


def chart_candidate(cands: list[Candidate]) -> Candidate | None:
    """종목 카드 중 선별 점수 1위 (동점은 source_select.rank_key: 거래량 → 수익률 → 최신순). 없으면 None."""
    stocks = [c for c in cands if is_stock_candidate(c)]
    return min(stocks, key=rank_key) if stocks else None


def with_stock_card(picked: list[Candidate], filler: Candidate | None, max_n: int) -> list[Candidate]:
    """종목 카드가 하나도 없으면 filler(시장 반응 1위 종목 움직임 카드)를 넣는다.

    자리가 차 있으면(max_n 장) 점수가 가장 낮은 카드를 뺀다. 순서는 원래 순서를 지키고 filler 는 맨 뒤.
    이미 종목 카드가 있거나 filler 가 없으면 그대로.
    """
    if filler is None or any(is_stock_candidate(c) for c in picked):
        return list(picked)
    if len(picked) < max_n:
        return [*picked, filler]
    lowest = max(picked, key=rank_key)
    return [c for c in picked if c is not lowest] + [filler]


def top_reactor(scores: pd.DataFrame, exclude: set[str] = frozenset(), caps: dict[str, float] | None = None,
                min_cap: float = MIN_MARKET_CAP) -> str | None:
    """그날 시장 반응이 가장 컸던 국내 보통주.

    scores: source_select.cross_section_scores 결과를 ticker 로 index 한 표 (vol_score, ret_score, score, abn_volume).
    caps: {ticker: 그날 시가총액(원)}. 있으면 min_cap 이상인 종목에서 먼저 고르고, 하나도 없으면 하한 없이 고른다.
    점수 1점 이상만. 동점은 거래량 점수 → 수익률 점수 → 평소 대비 거래량(abn_volume) → 코드 순. 없으면 None.
    """
    if caps:
        big = top_reactor(scores, exclude | {t for t in scores.index if caps.get(t, 0) < min_cap})
        if big is not None:
            return big
    if scores.empty or "score" not in scores.columns:  # 그날 국내 가격이 없으면 빈 표
        return None
    df = scores[[is_common(t) and t not in exclude for t in scores.index]]
    df = df[df["score"] >= 1]
    if df.empty:
        return None
    df = df.assign(_abn=df["abn_volume"].fillna(-math.inf), _t=df.index)
    df = df.sort_values(["score", "vol_score", "ret_score", "_abn", "_t"],
                        ascending=[False, False, False, False, True])
    return str(df.index[0])


def average_volume(volumes: list[float | None], n: int = VOLUME_LOOKBACK) -> float | None:
    """직전 n 거래일 평균 거래량 (값 없는 날은 뺀다). 평균할 날이 없거나 0 이면 None."""
    known = [v for v in volumes[-n:] if v is not None]
    avg = sum(known) / len(known) if known else 0
    return avg if avg > 0 else None


def build_source(ticker: str, name: str, day: date, close: float, prev_close: float,
                 volume: float | None, avg_volume: float | None, vol_score: int, ret_score: int,
                 same_day: list[dict]) -> dict:
    """raw_sources 한 줄 (collectors.sources.Source 와 같은 칸). numbers 는 compose 프롬프트에 '키: 값'으로 보인다."""
    chg = close / prev_close - 1
    numbers: dict = {
        "종목": f"{name}({ticker})",
        "기준일": day.isoformat(),
        "종가(원)": round(close),
        "전 거래일 종가(원)": round(prev_close),
        "등락률(%)": round(chg * 100, 2),
        "방향": direction_word(chg),
    }
    if volume is not None:
        numbers["거래량(주)"] = int(volume)
    if volume is not None and avg_volume:
        numbers[f"직전 {VOLUME_LOOKBACK}거래일 평균 거래량(주)"] = int(avg_volume)
        numbers["평소 대비 거래량(배)"] = round(volume / avg_volume, 1)
    numbers["선별 점수"] = f"거래량 {vol_score} + 수익률 {ret_score} = {vol_score + ret_score} (그날 시장 반응 1위 종목)"
    if same_day:
        for i, s in enumerate(same_day[:MAX_SAME_DAY], 1):
            numbers[f"같은 날 자료 {i}"] = s["title"]
    else:
        numbers["같은 날 자료"] = "이 종목에 대한 공시 없음"
    return {
        "source_type": "price",
        "source_key": f"{ticker}_{CATEGORY}_{day.isoformat()}",
        "category": CATEGORY,
        "title": f"{name} {abs(chg) * 100:.2f}% {direction_word(chg)} · 거래량 "
                 + (f"평소의 {volume / avg_volume:.1f}배" if volume is not None and avg_volume else "급변"),
        "url": f"https://finance.naver.com/item/main.naver?code={ticker}",
        "issuer_name": name,
        "ticker": ticker,
        "market": "KR",
        "published_date": day,
        "published_at": datetime.combine(day, MARKET_CLOSE, KST),
        "numbers": numbers,
    }


# ------------------------------------------------------------------
# 2. DB·네트워크
# ------------------------------------------------------------------

def recent_bars(conn, ticker: str, day: date, n: int = VOLUME_LOOKBACK + 1) -> list[tuple[date, float, float | None]]:
    """day 이하 최근 n 거래일 (날짜, 종가, 거래량), 오래된 순."""
    rows = conn.execute(
        """SELECT market_date, close, volume FROM prices WHERE ticker = %s AND market_date <= %s
           ORDER BY market_date DESC LIMIT %s""",
        (ticker, day, n),
    ).fetchall()
    return [(r[0], float(r[1]), None if r[2] is None else float(r[2])) for r in reversed(rows)]


def same_day_sources(conn, ticker: str, day: date) -> list[dict]:
    """그 종목 자료 중 직전 거래일 다음 날 ~ day 에 나온 것 (가격 카드 자신은 뺀다)."""
    prev = conn.execute(
        "SELECT max(market_date) FROM prices WHERE ticker = 'KS11' AND market_date < %s", (day,)
    ).fetchone()[0] or day - timedelta(days=1)
    cur = conn.execute(
        """SELECT id, source_type, category, title, issuer_name, ticker, published_date
           FROM raw_sources
           WHERE published_date > %s AND published_date <= %s AND source_type <> 'price' AND ticker = %s
           ORDER BY id""",
        (prev, day, ticker),
    )
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def save_source(conn, src: dict) -> dict:
    """raw_sources 에 넣고(이미 있으면 numbers 를 새 값으로) id 를 붙인 행을 돌려준다."""
    from psycopg.types.json import Jsonb

    row = conn.execute(
        """INSERT INTO raw_sources (source_type, source_key, category, title, url, issuer_name,
                                    ticker, market, published_date, published_at, numbers)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (source_type, source_key) DO UPDATE
               SET numbers = EXCLUDED.numbers, title = EXCLUDED.title
           RETURNING id""",
        (src["source_type"], src["source_key"], src["category"], src["title"], src["url"],
         src["issuer_name"], src["ticker"], src["market"], src["published_date"], src["published_at"],
         Jsonb(src["numbers"])),
    ).fetchone()
    return {**src, "id": row[0]}


def link_same_day(card_id: int, same_day: list[dict]) -> None:
    """같은 날 그 종목 자료를 카드 출처로 묶는다 (is_main = false). 출제에는 numbers 로만 들어가 있다."""
    from db import get_conn

    with get_conn() as conn:
        for s in same_day[:MAX_SAME_DAY]:
            conn.execute(
                """INSERT INTO card_sources (card_id, source_id, is_main) VALUES (%s, %s, false)
                   ON CONFLICT DO NOTHING""",
                (card_id, s["id"]),
            )


def stock_name(ticker: str) -> str:
    try:
        from pykrx import stock

        return stock.get_market_ticker_name(ticker) or ticker
    except Exception:  # noqa: BLE001 - 이름은 못 가져와도 코드로 카드를 만든다
        return ticker


def market_caps(day: date) -> dict[str, float] | None:
    """그날 국내 전 종목 시가총액 {ticker: 원} (pykrx). 못 받으면 None → 하한 없이 고른다."""
    try:
        from pykrx import stock

        from collectors.prices import kr_code, ymd

        df = stock.get_market_cap(ymd(day), market="ALL")
        if df.empty:
            return None
        return {kr_code(t): float(v) for t, v in zip(df.index.astype(str), df["시가총액"])}
    except Exception as e:  # noqa: BLE001 - 시가총액이 없어도 차트 카드는 만든다
        print(f"  시가총액을 못 받아 하한 없이 고릅니다: {type(e).__name__}: {e}")
        return None


def prepare(conn, target: date, scores: pd.DataFrame, exclude: set[str] = frozenset()) -> Candidate | None:
    """시장 반응 1위 종목의 움직임 자료를 raw_sources 에 저장하고 출제 후보로 돌려준다. 고를 종목이 없으면 None."""
    from generate.classify import ClassifyResult

    ticker = top_reactor(scores, set(exclude), market_caps(target))
    if ticker is None:
        return None
    bars = recent_bars(conn, ticker, target)
    if len(bars) < 2 or bars[-1][0] != target or not bars[-2][1]:
        return None
    volume = bars[-1][2]
    avg_volume = average_volume([b[2] for b in bars[:-1]])
    row = scores.loc[ticker]
    vol_score, ret_score = int(row["vol_score"]), int(row["ret_score"])
    same_day = same_day_sources(conn, ticker, target)
    src = save_source(conn, build_source(ticker, stock_name(ticker), target, bars[-1][1], bars[-2][1],
                                         volume, avg_volume, vol_score, ret_score, same_day))
    cls = ClassifyResult(card_type=1, start_concept=None, reason="차트 종목 카드: 유형은 코드가 1로 정함")
    return Candidate(source_id=str(src["id"]), event_key=ticker, published_at=src["published_at"],
                     vol_score=vol_score, ret_score=ret_score, card_type=1, is_price_card=True,
                     extra={"source": src, "classify": cls, "same_day": same_day})


def select_info(picked: list[Candidate], chart: Candidate | None) -> dict[int, dict]:
    """{card_id: model_info.select} — 출제된 카드마다 선별 점수와 차트 카드 여부."""
    out = {}
    for c in picked:
        card_id = c.extra.get("card_id")
        if card_id:
            out[card_id] = {"score": c.score, "vol_score": c.vol_score, "ret_score": c.ret_score,
                            "stock": is_stock_candidate(c), "chart": c is chart}
    return out


def save_select_info(info: dict[int, dict]) -> None:
    """cards.model_info 에 select 를 더한다 (스키마 변경 없이 JSONB 키 하나)."""
    from psycopg.types.json import Jsonb

    from db import get_conn

    with get_conn() as conn:
        for card_id, sel in info.items():
            conn.execute(
                "UPDATE cards SET model_info = coalesce(model_info, '{}'::jsonb) || %s WHERE id = %s",
                (Jsonb({"select": sel}), card_id),
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="시장 반응 1위 종목 (차트 종목 카드 자료)")
    parser.add_argument("date", help="기준 거래일 YYYY-MM-DD")
    parser.add_argument("--no-llm", action="store_true", help="자료만 저장하고 출력한다 (지금은 이 모드만)")
    args = parser.parse_args(argv)
    target = date.fromisoformat(args.date)

    from collectors.prices import load_volume_history
    from compute.source_select import cross_section_scores
    from db import get_conn
    from run_daily import kr_day_table

    with get_conn() as conn:
        table = kr_day_table(conn, target)
        scores = cross_section_scores(table, load_volume_history(conn, table["ticker"].tolist(), target))
        cand = prepare(conn, target, scores.set_index("ticker"))
        conn.commit()
    if cand is None:
        print("고를 종목이 없어요 (그날 국내 가격이 없거나 점수 1점 이상 종목이 없음)")
        return 1
    src = cand.extra["source"]
    print(f"{src['title']} · 점수 {cand.score} · 같은 날 자료 {len(cand.extra['same_day'])}건")
    for k, v in src["numbers"].items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
