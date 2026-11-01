"""compute/indicators.py 테스트. 손계산이 정답이고, C의 test_tools.py 계산 테스트와 같은 숫자가 나와야 한다."""
import random
from datetime import date

import pandas as pd
import pytest

from compute.indicators import pct_return, rsi_series, top_volume_days, volume_ratio, wilder_rsi


def test_rsi_hand_calc():
    # 종가 10, 11, 10, 12, 13 / period 2 → 변화 +1, -1, +2, +1
    # 첫 평균: 이익 (1+0)/2 = 0.5, 손실 (0+1)/2 = 0.5
    # +2: 이익 (0.5×1+2)/2 = 1.25, 손실 (0.5×1+0)/2 = 0.25
    # +1: 이익 (1.25+1)/2 = 1.125, 손실 0.25/2 = 0.125 → RS 9 → RSI 100 - 100/10 = 90
    assert wilder_rsi([10, 11, 10, 12, 13], period=2) == 90.0


def test_rsi_after_first_average():
    # 위에서 +2 까지만: RS = 1.25/0.25 = 5 → 100 - 100/6 = 83.33
    assert wilder_rsi([10, 11, 10, 12], period=2) == 83.33


def test_rsi_no_loss_is_100():
    assert wilder_rsi([1, 2, 3, 4], period=2) == 100.0


def test_rsi_too_short():
    with pytest.raises(ValueError):
        wilder_rsi([1, 2], period=2)


def test_rsi_series_hand_calc():
    # 위 손계산의 날짜별 값: 앞 2개는 변화가 모자라 None, 첫 평균 RS 1 → 50, 그다음 83.33, 90
    assert rsi_series([10, 11, 10, 12, 13], period=2) == [None, None, 50.0, 83.33, 90.0]


def test_rsi_series_matches_last_value_every_day():
    # 차트 선의 각 점이 그날까지 잘라서 계산한 wilder_rsi 와 같아야 한다 (화면과 출제 정답이 어긋나지 않게)
    rnd = random.Random(0)
    closes = [100.0]
    for _ in range(80):
        closes.append(closes[-1] * (1 + rnd.uniform(-0.03, 0.03)))
    series = rsi_series(closes, 14)
    for i in range(14, len(closes)):
        assert series[i] == wilder_rsi(closes[:i + 1], 14)


def test_rsi_series_short_input_is_all_none():
    assert rsi_series([1, 2], period=2) == [None, None]


def test_pct_return():
    assert pct_return(200, 210) == 5.0
    assert pct_return(80, 79) == -1.25


def test_volume_ratio():
    # 앞 3일 평균 (100+200+300)/3 = 200, 오늘 500 → 2.5배
    assert volume_ratio([100, 200, 300, 500]) == 2.5


def test_volume_ratio_needs_previous_day():
    with pytest.raises(ValueError):
        volume_ratio([500])


def test_top_volume_tie_earlier_first():
    df = pd.DataFrame({"market_date": [date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5)],
                       "volume": [300, 500, 500]})
    assert top_volume_days(df, 2) == [{"date": "2026-10-02", "volume": 500},
                                        {"date": "2026-10-05", "volume": 500}]
