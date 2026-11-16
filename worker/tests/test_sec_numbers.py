"""sec_numbers.py: SEC XBRL companyfacts → 8-K 실적 numbers (네트워크 없이).

모양은 2026-11-16 data.sec.gov/api/xbrl/companyfacts (MSFT) 와 같은 가짜 값이다. 기대값은 손으로 계산했다.
"""
from datetime import date

import pytest

from collectors import sec_numbers as sn


def _f(start, end, val, form="10-Q", filed="2026-04-29"):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed, "accn": "x", "fp": "Q", "fy": 2026}


def _facts(revenue, net, eps, tag="RevenueFromContractWithCustomerExcludingAssessedTax"):
    return {"facts": {"us-gaap": {
        tag: {"units": {"USD": revenue}},
        "NetIncomeLoss": {"units": {"USD": net}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": eps}},
    }}}


# 회계연도 7/1 시작 (MSFT 처럼). 3분기(1~3월)는 분기 값, 4분기(4~6월)는 연간만 있다
REVENUE = [
    _f("2025-01-01", "2025-03-31", 70_066e6, filed="2025-04-30"),
    _f("2025-04-01", "2025-06-30", 76_441e6, filed="2025-07-30"),
    _f("2026-01-01", "2026-03-31", 82_886e6),
    _f("2025-07-01", "2026-03-31", 241_832e6),               # 9개월 누계
    _f("2025-07-01", "2026-06-30", 331_839e6, "10-K", "2026-07-29"),  # 연간
    _f("2026-01-01", "2026-03-31", 82_000e6, filed="2026-01-01"),     # 먼저 접수된 다른 값 → 늦게 접수된 값을 쓴다
]
NET = [
    _f("2025-01-01", "2025-03-31", -50e6, filed="2025-04-30"),
    _f("2026-01-01", "2026-03-31", 31_778e6),
]
EPS = [
    _f("2025-01-01", "2025-03-31", 3.46, filed="2025-04-30"),
    _f("2026-01-01", "2026-03-31", 4.27),
    _f("2025-07-01", "2026-03-31", 13.14),
    _f("2025-07-01", "2026-06-30", 17.95, "10-K", "2026-07-29"),
]
FACTS = _facts(REVENUE, NET, EPS)


def test_quarter_after_8k_with_yoy_and_turn():
    n = sn.earnings_numbers(FACTS, date(2026, 4, 29))
    assert n["실적기간"] == "2026-01-01~2026-03-31"
    # 82,886 ÷ 70,066 − 1 = 18.297% → 18.3, 백만달러
    assert (n["매출액"], n["매출액 전년동기"], n["매출액 전년동기대비(%)"]) == (82886, 70066, 18.3)
    assert n["매출액 전년동기대비 방향"] == "증가"
    # 순이익 -50 → 31,778: 부호가 바뀌면 % 대신 흑자전환
    assert n["당기순이익 전년동기대비 방향"] == "흑자전환" and "당기순이익 전년동기대비(%)" not in n
    # 주당순이익은 달러 그대로: 4.27 ÷ 3.46 − 1 = 23.41% → 23.4
    assert (n["주당순이익(희석)"], n["주당순이익(희석) 전년동기대비(%)"]) == (4.27, 23.4)


def test_fiscal_q4_is_year_minus_nine_months_without_eps():
    n = sn.earnings_numbers(FACTS, date(2026, 7, 29))
    # 331,839 − 241,832 = 90,007. 전년 4분기 76,441 → 90,007 ÷ 76,441 − 1 = 17.75% → 17.7
    assert n["실적기간"] == "2026-04-01~2026-06-30"
    assert (n["매출액"], n["매출액 전년동기대비(%)"]) == (90007, 17.7)
    # 주당순이익은 연간 − 9개월로 빼면 맞지 않아(17.95 − 13.14 = 4.81 근삿값) 넣지 않는다
    assert not any(k.startswith("주당순이익") for k in n)


def test_no_quarter_within_lag_is_empty():
    # 3/31 분기 끝 → 7/1 은 92일 뒤라 (75일 초과) 그 분기 실적 발표로 보지 않는다. 6/30 분기는 아직 끝나지 않음
    assert sn.earnings_numbers(FACTS, date(2026, 6, 25)) == {}
    assert sn.earnings_numbers({"facts": {}}, date(2026, 4, 29)) == {}


def test_revenue_tag_fallback():
    facts = _facts(REVENUE, NET, EPS, tag="Revenues")
    assert sn.earnings_numbers(facts, date(2026, 4, 29))["매출액"] == 82886


@pytest.mark.parametrize("prev,cur,want", [(-1, 2, "흑자전환"), (1, -2, "적자전환"), (-1, -2, "적자지속"),
                                           (1, 2, None), (0, -1, "적자전환")])
def test_turn(prev, cur, want):
    assert sn.turn(prev, cur) == want


def test_fill_fetches_each_ticker_once_and_updates(monkeypatch):
    calls, executed = [], []
    monkeypatch.setattr(sn, "fetch_facts", lambda cik: calls.append(cik) or FACTS)

    class Conn:
        def execute(self, sql, params):
            executed.append(params)

    rows = [(1, "MSFT", date(2026, 4, 29)), (2, "MSFT", date(2026, 7, 29)), (3, "ZZZZ", date(2026, 4, 29))]
    n = sn.fill(Conn(), rows, {"MSFT": 789019}, save=True)
    assert n == 2 and calls == [789019]  # 같은 티커는 한 번만, CIK 없는 티커는 건너뜀
    assert [p[1] for p in executed] == [1, 2]
    assert '"매출액": 82886' in executed[0][0]
