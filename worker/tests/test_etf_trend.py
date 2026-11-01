from datetime import date
from decimal import Decimal as D

from compute.etf_trend import chg_pct, compute_changes, previous_date, summarize, trend_base_date

# 수집 시작 9/30, 휴장일 10/5·10/9 는 스냅샷이 없다
DATES = [date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 6), date(2026, 10, 8)]


def test_chg_pct_hand_calc():
    # NVIDIA 1CU 239 -> 250: (250 - 239) / 239 = 0.0460251...
    assert chg_pct(D("250"), D("239")) == 0.046025
    # KoAct 소수 수량 99.88 -> 94.886: -0.05
    assert chg_pct(D("94.886"), D("99.88")) == -0.05
    assert chg_pct(D("100"), D("100")) == 0.0


def test_chg_pct_null_when_no_previous():
    # P2: 이전 값이 없거나 0이면 NULL (신규 편입을 무한대로 만들지 않음)
    assert chg_pct(D("10"), None) is None
    assert chg_pct(D("10"), D("0")) is None


def test_trend_base_date_is_quarter_end_snapshot():
    assert trend_base_date(date(2026, 10, 8), DATES) == date(2026, 9, 30)
    assert trend_base_date(date(2026, 9, 30), DATES) == date(2026, 9, 30)  # 분기 말 당일은 자기 자신


def test_trend_base_date_falls_back_to_first_snapshot_after_quarter_end():
    # 10/2 부터 수집했다면 기준일은 수집 시작일 (P15)
    started_late = DATES[2:]
    assert trend_base_date(date(2026, 10, 8), started_late) == date(2026, 10, 2)


def test_trend_base_date_resets_next_quarter():
    # 12/31 은 KRX 휴장이라 4분기 기준은 다음 해 첫 스냅샷
    dates = [date(2026, 12, 30), date(2027, 1, 4), date(2027, 1, 5)]
    assert trend_base_date(date(2027, 1, 5), dates) == date(2027, 1, 4)
    # 12/30 은 아직 3분기(9/30 기준) 소속. 이 목록엔 그 앞 스냅샷이 없어서 자기 자신이 수집 시작일
    assert trend_base_date(date(2026, 12, 30), dates) == date(2026, 12, 30)
    assert trend_base_date(date(2026, 9, 29), dates) is None  # 분기 말 이후 스냅샷이 없음


def test_previous_date_skips_holidays():
    assert previous_date(date(2026, 10, 6), DATES) == date(2026, 10, 2)  # 10/5 휴장
    assert previous_date(date(2026, 9, 30), DATES) is None


def test_compute_changes_trend_and_day():
    base = {"7066G1": D("239"), "378331": D("120"), "8160R1": D("50")}
    prev = {"7066G1": D("245"), "378331": D("120")}
    curr = {"7066G1": D("250"), "378331": D("114"), "079031": D("40")}  # 8160R1 편출, 079031 신규
    out = compute_changes(curr, base, prev)
    assert out == {
        "7066G1": (0.046025, 0.020408),   # 추세 (250-239)/239, 전일 (250-245)/245
        "378331": (-0.05, -0.05),         # (114-120)/120
        "079031": (None, None),           # 신규 편입
    }
    assert "8160R1" not in out             # 편출 종목은 그날 행이 없어 채우지 않는다


def test_summarize_uses_threshold():
    changes = {"a": (0.06, None), "b": (-0.05, None), "c": (0.01, None), "d": (None, None)}
    assert summarize(changes, threshold=0.05) == {"늘림": 1, "줄임": 1, "변화 작음": 1, "신규": 1}
