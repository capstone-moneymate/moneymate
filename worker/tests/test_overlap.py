from datetime import date
from decimal import Decimal

import pytest

from compute.overlap import (
    big_direction, build_results, co_increased, compare, etf_change, etf_direction, etf_entry,
)


def test_big_direction_threshold_5pct():
    assert big_direction("increase", 0.05) == "up"        # 임계값과 같으면 늘림
    assert big_direction("increase", 0.049) is None       # 기준 미만 -> none
    assert big_direction("decrease", -0.05) == "down"
    assert big_direction("decrease", -0.01) is None
    assert big_direction("unchanged", 0.0) is None
    assert big_direction("new", None) == "up"             # P13: new 는 늘림
    assert big_direction("exit", -1.0) == "down"


def test_etf_change_1cu_decimal():
    # KoAct NVIDIA 99.88 -> 104.874: (104.874 - 99.88) / 99.88 = 4.994 / 99.88 = 0.05
    assert etf_change(Decimal("99.88"), Decimal("104.874")) == ("held", 0.05)
    assert etf_change(Decimal("239"), Decimal("239")) == ("held", 0.0)
    assert etf_change(None, Decimal("10")) == ("new", None)
    assert etf_change(Decimal("10"), None) == ("exit", -1.0)
    assert etf_change(None, None) == ("none", None)


def test_etf_direction():
    assert etf_direction("held", 0.05) == "up"
    assert etf_direction("held", 0.0) is None
    assert etf_direction("new", None) == "up"
    assert etf_direction("exit", -1.0) == "down"


def test_compare():
    assert compare("up", "up") == "same"
    assert compare("up", "down") == "diff"
    assert compare(None, "up") == "none"
    assert compare("down", None) == "none"


def test_build_results_hand_example():
    period, today = date(2026, 6, 30), date(2026, 10, 29)
    big = [
        {"filer_key": "buffett", "cusip": "67066G104", "ticker": "NVDA", "change_type": "increase", "chg_pct": 0.10},
        {"filer_key": "thiel", "cusip": "023135106", "ticker": "AMZN", "change_type": "new", "chg_pct": None},
        {"filer_key": "ackman", "cusip": "999999999", "ticker": None, "change_type": "new", "chg_pct": None},
    ]
    etfs = {
        # TIME: NVIDIA 239 -> 200 (줄임), Amazon 10 -> 없음 (exit)
        "426030": {"latest_date": date(2026, 10, 28),
                   "base": {"7066G1": Decimal("239"), "231351": Decimal("10")},
                   "latest": {"7066G1": Decimal("200")}},
        # KoAct: NVIDIA 99.88 -> 104.874 (+5%, 늘림), Amazon 은 보유 안 함
        "0015B0": {"latest_date": date(2026, 10, 28),
                   "base": {"7066G1": Decimal("99.88")},
                   "latest": {"7066G1": Decimal("104.874")}},
    }
    got = {(r["ticker"], r["filer_key"], r["etf_code"]): (r["direction"], r["etf_trend_chg_pct"])
           for r in build_results(big, etfs, period, today)}
    assert got == {
        ("NVDA", "buffett", "426030"): ("diff", -0.16318),   # 큰손 +10% 늘림 vs (200-239)/239 = -0.163180 줄임
        ("NVDA", "buffett", "0015B0"): ("same", 0.05),       # 늘림 vs 늘림
        ("AMZN", "thiel", "426030"): ("diff", -1.0),         # 신규 매수 vs ETF 전량 정리
    }
    # 티커 없는 ackman 행과 KoAct-AMZN(둘 다 없음)은 만들지 않는다


def test_common_shift_is_removed_before_direction():
    # KoAct 11/10 처럼 6종목이 다 같이 ×1.064 로 밀린 날이 사이에 있다. RAW006 만 그날 실제로 더 사서 120
    period, today = date(2026, 9, 30), date(2026, 11, 19)
    codes = [f"RAW00{i}" for i in range(1, 7)]   # CUSIP 2~7번째 글자 (6자리)
    d0, d1, d2 = date(2026, 9, 30), date(2026, 11, 10), date(2026, 11, 18)
    base = {c: Decimal("100") for c in codes}
    shifted = {c: Decimal("106.4") for c in codes[:5]} | {"RAW006": Decimal("120")}
    e = etf_entry({d0: base, d1: shifted, d2: dict(shifted)})
    assert e["base_date"] == d0 and e["latest_date"] == d2
    assert e["factor"] == pytest.approx(1.064) and e["shift_days"] == [d1]

    big = [{"filer_key": "buffett", "cusip": "0RAW001X0", "ticker": "AAA", "change_type": "increase", "chg_pct": 0.10},
           {"filer_key": "buffett", "cusip": "0RAW006X0", "ticker": "FFF", "change_type": "increase", "chg_pct": 0.10}]
    got = {r["ticker"]: (r["direction"], r["etf_trend_chg_pct"])
           for r in build_results(big, {"0015B0": e}, period, today)}
    # 손계산: 106.4 ÷ 1.064 = 100 → 0% (보정 전이면 +6.4% 늘림으로 same 이 됐다)
    #         120 ÷ 1.064 = 112.78 → +12.782% (실제 매매만 남아 늘림)
    assert got == {"AAA": ("none", 0.0), "FFF": ("same", 0.12782)}


def test_no_shift_keeps_old_result():
    # 공통 이동일이 없으면 배수 1 이라 예전 계산과 같다 (TIME 3분기)
    e = etf_entry({date(2026, 9, 30): {"A": Decimal("239")}, date(2026, 11, 18): {"A": Decimal("200")}})
    assert e["factor"] == 1.0 and e["shift_days"] == []
    assert e["latest"] == {"A": Decimal("200")}


def test_co_increased_two_or_more():
    dirs = {"NVDA": {"buffett": "up", "thiel": "up", "ackman": "down"},
            "AAPL": {"buffett": "up", "druckenmiller": None}}
    assert co_increased(dirs) == {"NVDA": ["buffett", "thiel"]}
