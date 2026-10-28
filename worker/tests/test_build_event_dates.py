"""build_event_dates.index_events: 앞쪽 기간은 계산에만 쓰고, 고르기는 start 이후에서만 (CodeRabbit 리뷰, PR #22)."""
from datetime import date, timedelta

import pandas as pd

from scripts.build_event_dates import N_EXTREME, index_events

START = date(2026, 1, 1)


def _frame(returns: list[float], first_day: date, volumes: list[int] | None = None) -> pd.DataFrame:
    closes, c = [], 100.0
    for r in returns:
        c *= 1 + r
        closes.append(c)
    days = [first_day + timedelta(days=i) for i in range(len(returns))]
    return pd.DataFrame({"market_date": days, "close": closes, "volume": volumes or [1000] * len(returns)})


def test_top_events_are_picked_inside_period_only():
    # 앞쪽 300일: +20% 급등 6번 (기간 밖). 기간 안 60일: 짝수 날 +1·+3·+5%, 홀수 날 -2·-4·-6%
    look = [0.2 if i % 50 == 10 else 0.0 for i in range(300)]
    period = [(-1) ** i * (0.01 + (i % 6) * 0.01) for i in range(60)]
    df = _frame(look + period, START - timedelta(days=300))
    rows = index_events(df, "KS11", START)
    rises = [r for r in rows if r["event_type"] == "big_rise"]
    # 예전 방식이면 상위 4개가 모두 앞쪽 +20% 날이라 버려져 0개가 됐다
    assert len(rises) == N_EXTREME
    assert all(r["event_date"] >= START for r in rows)
    assert {r["value"] for r in rises} == {0.05}  # 기간 안 가장 큰 상승 +5% 날들


def test_streak_counts_days_before_start():
    # start 전 3일 + start 후 2일 연속 상승 → start 후 끝난 구간 길이는 5
    look = [0.0] * 10 + [0.01, 0.01, 0.01]
    period = [0.01, 0.01, -0.01, 0.0]
    df = _frame(look + period, START - timedelta(days=13))
    streaks = [r for r in index_events(df, "KS11", START) if r["event_type"] == "consecutive_rise"]
    assert streaks[0]["event_date"] == START + timedelta(days=1)
    assert streaks[0]["value"] == 5
