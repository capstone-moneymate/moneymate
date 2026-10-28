"""이벤트 날짜표(db/seeds/event_dates.csv) 만들기 (C). 차트 읽기의 "비슷했던 과거의 날"을 고르는 표다.

기술확정안: 자동으로 찾지 않고 팀이 만든 표(금리 결정일, 급등락일 등 20~30개)에서 고른다.
이 스크립트는 후보를 데이터로 뽑아 CSV로 쓰고, 팀이 note 를 보고 남길 줄을 정한다 (사람이 고른 뒤 커밋).

실행: cd worker && python scripts/build_event_dates.py [시작일 2024-01-01]
뽑는 것 (지수 KS11·IXIC, 시작일~오늘):
  - big_rise / big_drop: 일간 수익률 상·하위 4일씩
  - volume_spike: 비정상 거래량(그날 ÷ 직전 252거래일 평균) 상위 4일 (개념 volume_spike)
  - consecutive_rise: 가장 긴 연속 상승 구간 2개의 마지막 날 (개념 consecutive_rise)
  - rate_decision: collectors/macro_calendar.csv 중 verified=Y 이고 이미 발표된 날.
    rate_hike·rate_cut·rate_hold 를 한은은 ECOS 기준금리(ECOS_API_KEY 필요), FOMC 는 FRED 목표 상단으로 채운다
숫자는 모두 코드가 계산한다. 같은 날이 여러 종류로 뽑히면 한 줄씩 따로 남긴다.
"""
import csv
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.prices import fetch_index  # noqa: E402
from collectors.sources import fetch_bok_rate, fetch_fed_rate, load_macro_calendar  # noqa: E402

OUT = ROOT.parent / "db" / "seeds" / "event_dates.csv"
COLUMNS = ["event_date", "market", "ticker", "event_type", "concept_id", "value", "note", "source"]
N_EXTREME = 4


def index_events(df: pd.DataFrame, key: str, start: date) -> list[dict]:
    """수익률·252일 평균 거래량·연속 상승 길이는 앞쪽 기간(lookback)까지 써서 계산하고,
    상위 N개는 start 이후 날짜 중에서만 고른다.

    처음엔 전체에서 고른 뒤 start 이전을 버려서 줄 수가 모자랐다 (CodeRabbit 리뷰, PR #23).
    """
    df = df.sort_values("market_date").reset_index(drop=True)
    df["ret"] = df["close"].pct_change()
    df["abn_vol"] = df["volume"] / df["volume"].shift(1).rolling(252).mean()
    up = (df["ret"] > 0).astype(int)
    df["streak"] = up.groupby((up == 0).cumsum()).cumsum()  # 오른 날이 이어진 길이
    is_end = (df["streak"] > 0) & (df["streak"].shift(-1, fill_value=0) == 0)  # 연속 상승 구간의 마지막 날
    df = df[df["market_date"] >= start]
    rows = []

    def row(r, event_type, concept, value, note):
        rows.append({"event_date": r.market_date, "market": "INDEX", "ticker": key, "event_type": event_type,
                     "concept_id": concept, "value": round(float(value), 4), "note": note,
                     "source": "FinanceDataReader"})

    for r in df.nlargest(N_EXTREME, "ret").itertuples():
        row(r, "big_rise", "", r.ret, f"{key} 하루 {r.ret:+.2%}")
    for r in df.nsmallest(N_EXTREME, "ret").itertuples():
        row(r, "big_drop", "", r.ret, f"{key} 하루 {r.ret:+.2%}")
    vol = df[df["volume"] > 0].dropna(subset=["abn_vol"])
    for r in vol.nlargest(N_EXTREME, "abn_vol").itertuples():
        row(r, "volume_spike", "volume_spike", r.abn_vol, f"{key} 거래량 252일 평균의 {r.abn_vol:.1f}배")

    # 연속 상승: 구간 마지막 날에 길이를 남긴다. 구간이 start 전에 시작했어도 끝난 날이 기간 안이면 넣는다
    ends = df[is_end[df.index]]
    for r in ends.nlargest(2, "streak").itertuples():
        row(r, "consecutive_rise", "consecutive_rise", r.streak, f"{key} {int(r.streak)}거래일 연속 상승")
    return rows


def rate_events(start: date) -> list[dict]:
    rows = []
    for c in load_macro_calendar():
        at = datetime.fromisoformat(c["announce_at"])
        if c["verified"] != "Y" or at.date() < start or at > datetime.now(at.tzinfo):  # 아직 발표 전이면 뺀다
            continue
        row = {"event_date": at.date(), "market": "INDEX", "ticker": c["target"], "event_type": "rate_decision",
               "concept_id": "", "value": "", "note": f'{c["title"]} (인상·동결·인하는 발표문 확인 후 concept_id 채움)',
               "source": c["url"]}
        # 결정 전·후 금리로 rate_hike·rate_cut·rate_hold 를 코드가 채운다. 한은은 ECOS, FOMC 는 FRED 목표 상단
        change, source = None, ""
        if c["kind"] == "bok_rate" and os.getenv("ECOS_API_KEY"):
            change, source = fetch_bok_rate(at.date()), "ECOS 722Y001"
        elif c["kind"] == "fomc":
            change, source = fetch_fed_rate(at.date()), "FRED DFEDTARU"
        if change:
            row.update(concept_id=f'rate_{change["decision"]}', value=change["rate_after"],
                       note=f'{c["title"]} {change["rate_before"]}% → {change["rate_after"]}%', source=source)
        rows.append(row)
    return rows


def main(argv: list[str]) -> int:
    start = date.fromisoformat(argv[0]) if argv else date(2024, 1, 1)
    rows: list[dict] = []
    for key in ("KS11", "IXIC"):
        # 252일 평균을 내려고 시작일보다 400일 앞부터 받는다
        df = fetch_index(key, start - timedelta(days=400), date.today())
        rows += index_events(df, key, start)
    rows += rate_events(start)
    rows.sort(key=lambda r: (r["event_date"], r["ticker"], r["event_type"]))
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)}줄 → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
