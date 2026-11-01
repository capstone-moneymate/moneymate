from datetime import date
from decimal import Decimal

from compute.overlap import big_direction, build_results, co_increased, compare, etf_change, etf_direction


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


def test_co_increased_two_or_more():
    dirs = {"NVDA": {"buffett": "up", "thiel": "up", "ackman": "down"},
            "AAPL": {"buffett": "up", "druckenmiller": None}}
    assert co_increased(dirs) == {"NVDA": ["buffett", "thiel"]}
