from datetime import date
from decimal import Decimal as D

import pytest

from compute.etf_shift import SHIFT_SHARE, adjust, common_shift, day_shift
from compute.etf_trend import chg_pct, compute_changes, shift_factors


def snap(values):
    """종목 C00..Cnn 의 수량."""
    return {f"C{i:02d}": D(str(v)) for i, v in enumerate(values)}


BASE = snap([100] * 6)


def test_a_hand_calc_common_shift_and_real_trade():
    # A 와 맞춘 예시: 공통 이동일 m = 1.064. 5종목은 같이 밀려 106.4, 1종목(C05)은 그날 더 사서 110
    curr = snap([106.4] * 5 + [110])
    m = day_shift(BASE, curr)
    assert m == pytest.approx(1.064)                       # 중앙값 1.064, 6종목 중 5종목(83%)이 같이 움직임
    assert adjust(D("106.4"), m) == pytest.approx(D("100"))  # 106.4 ÷ 1.064 = 100 → 추세 0%
    assert chg_pct(adjust(D("106.4"), m), D("100")) == 0.0
    # 110 ÷ 1.064 = 103.383... → 추세 +3.38% (실제 매매만 남음)
    assert chg_pct(adjust(D("110"), m), D("100")) == pytest.approx(0.033835, abs=1e-6)


def test_two_days_that_cancel_leave_trend_unchanged():
    # KoAct 11/10 +6.40%, 11/13 −6.72% 처럼 밀렸다가 되돌아가면 배수는 두 비율의 곱
    d0, d1, d2 = date(2026, 11, 9), date(2026, 11, 10), date(2026, 11, 13)
    day1 = {k: v * D("1.064") for k, v in BASE.items()}
    day2 = {k: v * D("0.9328") for k, v in day1.items()}
    s = common_shift({d0: BASE, d1: day1, d2: day2})
    assert s.days == [d1, d2]                              # 11/12 는 수집 빠짐 → 11/13 은 11/10 과 비교
    assert s.factor == pytest.approx(1.064 * 0.9328)       # 0.99250
    assert chg_pct(adjust(day2["C00"], s.factor), BASE["C00"]) == 0.0


@pytest.mark.parametrize("together, detected", [
    (44, True),   # 50종목 중 44종목(88%): 2026-11-10·11-13 KoAct 와 같은 비율. 70% 기준에서 잡혀야 한다 (A 요청)
    (35, True),   # 35/50 = 70% 는 경계 포함
    (34, False),  # 34/50 = 68% (2026-10-19 KoAct 67% 처럼) 는 공통 이동일이 아니다
])
def test_share_threshold_70_percent(together, detected):
    assert SHIFT_SHARE == 0.7
    prev = snap([100] * 50)
    # together 종목은 ×1.064, 나머지는 제각각 실제 매매 (중앙값은 1.064 쪽에 있도록 큰 쪽으로 흩음)
    others = [100 * (1.2 + 0.05 * i) for i in range(50 - together)]
    curr = snap([106.4] * together + others)
    m = day_shift(prev, curr)
    assert (m is not None) == detected
    if detected:
        assert m == pytest.approx(1.064)


def test_normal_trading_is_not_a_shift():
    # 운용사가 일부만 사고팔면 비율이 제각각이고 중앙값도 1 근처
    assert day_shift(BASE, snap([100, 100, 110, 90, 100, 130])) is None


def test_small_move_is_not_a_shift():
    # 중앙값 +0.4% 는 반올림·잡음 (MIN_MOVE 0.5% 이하)
    assert day_shift(BASE, snap([100.4] * 6)) is None
    # +0.6% 는 공통 이동
    assert day_shift(BASE, snap([100.6] * 6)) == pytest.approx(1.006)


def test_fractional_rounding_still_counts_as_same_ratio():
    # KoAct 소수 수량은 반올림 때문에 정확히 같은 비율이 아니다 (±0.5% 안)
    assert day_shift(BASE, snap([102, 102.2, 101.9, 102, 102.1, 102])) == pytest.approx(1.02)


def test_too_few_common_stocks_or_empty():
    assert day_shift(snap([100] * 4), snap([106.4] * 4)) is None  # 4종목 < 5
    assert day_shift({}, BASE) is None
    assert common_shift({}).factor == 1.0
    assert common_shift({date(2026, 9, 30): BASE}).days == []     # 기준일 하나뿐이면 비교 대상 없음


def test_new_and_exited_stocks_are_ignored():
    # 신규 편입(C06)·편출(C05)은 두 날 모두 있는 종목이 아니라 판정에서 빠진다
    prev = snap([100] * 6)
    curr = {k: v * D("1.064") for k, v in prev.items() if k != "C05"} | {"C06": D("50")}
    assert day_shift(prev, curr) == pytest.approx(1.064)


def test_adjust_keeps_value_when_no_shift():
    assert adjust(D("99.88"), 1.0) == D("99.88")
    assert adjust(None, 1.064) is None


def test_etf_trend_uses_factors():
    # 기준 9/30 100주, 11/10 공통 이동 +6.4%, 그날 C05 만 실제로 더 삼
    d0, d1, d2 = date(2026, 9, 30), date(2026, 11, 9), date(2026, 11, 10)
    day1 = dict(BASE)
    day2 = snap([106.4] * 5 + [110])
    snaps = {d0: BASE, d1: day1, d2: day2}
    trend_factor, day_factor = shift_factors(d2, d0, d1, snaps)
    assert trend_factor == pytest.approx(1.064) and day_factor == pytest.approx(1.064)
    out = compute_changes(day2, BASE, day1, trend_factor, day_factor)
    assert out["C00"] == (0.0, 0.0)                                    # 같이 밀린 종목: 추세·전일 모두 0
    assert out["C05"] == (pytest.approx(0.033835, abs=1e-6),) * 2      # 실제 매매만 남음
    # 보정이 없던 날은 예전 계산과 같다
    assert shift_factors(d1, d0, d0, snaps) == (1.0, 1.0)
