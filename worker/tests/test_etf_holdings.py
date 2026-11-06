from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from collectors import etf_holdings
from collectors.etf_holdings import (
    HOLDING_COLUMNS,
    collect_day,
    fetch_trading_day,
    fill_tickers,
    holdings_from_pykrx,
    latest_trading_day,
    main,
    same_company,
    unit_change_ratio,
)


def pdf(rows):
    """pykrx 구성종목 표 모양: index=코드, 컬럼 구성종목명·계약수·금액·시가총액·비중."""
    codes, names, shares = zip(*rows)
    return pd.DataFrame({"구성종목명": names, "계약수": shares, "금액": 0, "시가총액": 0, "비중": 0},
                        index=pd.Index(codes, name="티커"))


def test_holdings_from_pykrx_keeps_only_stocks():
    # findings.md B칸 TIME 10/8: 원화현금·설정현금액·나스닥100 선물 줄이 섞여 온다
    raw = pdf([
        ("7066G1", "NVIDIA CORP", 239),
        ("378331", "APPLE INC", 120),
        ("010010", "원화현금", 1520000),
        ("H00000", "설정현금액", 992000000),
        ("NQZ6", "NASDAQ 100 E-MINI 2026-12", 1),
    ])
    out = holdings_from_pykrx(raw, "426030", date(2026, 10, 8))
    assert list(out.columns) == ["etf_code", "snapshot_date", "raw_code", "stock_name", "shares"]
    assert out["raw_code"].tolist() == ["7066G1", "378331"]
    assert out["etf_code"].unique().tolist() == ["426030"]
    assert out["snapshot_date"].unique().tolist() == [date(2026, 10, 8)]


def test_holdings_from_pykrx_keeps_fractional_shares_exact():
    # KoAct NVIDIA 99.88: float 오차 없이 Decimal 로 (NUMERIC 컬럼)
    out = holdings_from_pykrx(pdf([("7066G1", "NVIDIA Corp", 99.88)]), "0015b0", date(2026, 10, 8))
    assert out["shares"].tolist() == [Decimal("99.88")]
    assert out["etf_code"].iloc[0] == "0015B0"  # 영문 섞인 ETF 코드는 대문자로


def test_holdings_from_pykrx_sums_duplicates_and_drops_zero():
    raw = pdf([
        ("7066G1", "NVIDIA CORP", 100),
        ("7066G1", "NVIDIA CORP", 39),     # 같은 코드 두 줄 → 합침
        ("8160R1", "TESLA INC", 0),        # 수량 0 → 보유 아님
    ])
    out = holdings_from_pykrx(raw, "426030", date(2026, 10, 8))
    assert out.set_index("raw_code")["shares"].to_dict() == {"7066G1": Decimal("139")}


def prev_curr(ratios):
    prev = {f"C{i:05d}": Decimal(100) for i in range(len(ratios))}
    curr = {k: Decimal(100) * Decimal(str(r)) for k, r in zip(prev, ratios)}
    return prev, curr


def test_unit_change_detected_when_all_scale_together():
    # 설정 단위 2배: 전 종목 100 → 200
    prev, curr = prev_curr([2, 2, 2, 2, 2, 2])
    assert unit_change_ratio(prev, curr) == 2.0


def test_unit_change_allows_rounding_in_fractional_shares():
    # KoAct 소수 수량은 반올림 때문에 정확히 같은 비율이 아닐 수 있다 (0.5% 안)
    prev, curr = prev_curr([2, 2.004, 1.998, 2, 2.001, 2])
    assert unit_change_ratio(prev, curr) is not None


def test_no_unit_change_for_normal_trading():
    # 운용사가 일부만 사고팔면 비율이 제각각
    prev, curr = prev_curr([1, 1, 1.1, 0.9, 1, 1.3])
    assert unit_change_ratio(prev, curr) is None


def test_no_unit_change_when_nothing_changed():
    prev, curr = prev_curr([1, 1, 1, 1, 1, 1])
    assert unit_change_ratio(prev, curr) is None


def test_no_unit_change_with_too_few_common_or_no_previous():
    prev, curr = prev_curr([2, 2, 2, 2])  # 겹치는 종목 4개 < 5
    assert unit_change_ratio(prev, curr) is None
    assert unit_change_ratio({}, curr) is None


@pytest.mark.parametrize("stock_name, issuer_name", [
    # 왼쪽은 2026-11-05 pykrx 실제 표기, 오른쪽은 13F 에서 쓰는 약칭 형식
    ("TESLA MOTORS", "TESLA INC"),
    ("BROADCOM LTD", "BROADCOM INC"),
    ("AMAZON.COM INC", "AMAZON COM INC"),
    ("COCA-COLA CO/THE", "COCA COLA CO"),
    ("ELI LILLY & CO", "LILLY ELI & CO"),
    ("Meta Platforms Inc-CL A", "META PLATFORMS INC"),
    ("TAIWAN SEMICONDUCTOR-SP ADR", "TAIWAN SEMICONDUCTOR MFG LTD"),
    ("TEXAS INSTRUMENTS INC", "TEXAS INSTRS INC"),
    ("APPLIED MATERIALS INC", "APPLIED MATLS INC"),
])
def test_same_company_allows_different_spellings(stock_name, issuer_name):
    assert same_company(stock_name, issuer_name)


@pytest.mark.parametrize("stock_name, issuer_name", [
    ("NVIDIA CORP", "APPLE INC"),
    ("ARM Holdings PLC", "NEBIUS GROUP NV"),         # 회사 형태 단어만 비슷함
    ("SEAGATE TECHNOLOGY", "DELL TECHNOLOGIES INC"),
    ("NVIDIA CORP", None),                           # 13F 발행사명이 없으면 확인할 수 없음
])
def test_same_company_rejects_other_companies(stock_name, issuer_name):
    assert not same_company(stock_name, issuer_name)


class FakeResult:
    def __init__(self, rows=(), rowcount=0):
        self._rows, self.rowcount = rows, rowcount

    def fetchall(self):
        return self._rows


class FakeConn:
    """fill_tickers 가 읽는 후보 줄을 돌려주고, UPDATE 인자를 모은다."""

    def __init__(self, candidates):
        self.candidates, self.updates = candidates, []

    def execute(self, sql, params=None):
        if sql.lstrip().startswith("UPDATE"):
            self.updates.append(params)
            return FakeResult(rowcount=21)
        return FakeResult(self.candidates)


def test_fill_tickers_skips_and_reports_different_company(capsys):
    # 000123 은 ETF 에만 있는 종목이 13F 의 다른 회사와 6자리가 겹친 경우
    conn = FakeConn([
        ("000123", "ETF ONLY CORP", "AAPL", "APPLE INC"),
        ("7066G1", "NVIDIA CORP", "NVDA", "NVIDIA CORPORATION"),
    ])
    assert fill_tickers(conn) == 21
    assert conn.updates == [("NVDA", "7066G1", "NVIDIA CORP")]
    out = capsys.readouterr().out
    assert "ticker 안 채움 (종목명 다름): 000123 ETF ONLY CORP ≠ AAPL APPLE INC" in out
    assert "ticker 채움: 7066G1 NVIDIA CORP → NVDA NVIDIA CORPORATION" in out


def test_latest_trading_day_uses_same_calendar_as_backfill(monkeypatch):
    # 토요일에 돌리면 달력의 마지막 거래일(금요일)
    calls = []

    def fake_days(end, n):
        calls.append((end, n))
        return [date(2026, 11, 6)]

    monkeypatch.setattr("collectors.prices.kr_trading_days", fake_days)
    assert latest_trading_day(date(2026, 11, 7)) == date(2026, 11, 6)
    assert calls == [(date(2026, 11, 7), 1)]


EMPTY = pd.DataFrame(columns=HOLDING_COLUMNS)
ONE_ROW = holdings_from_pykrx(pdf([("7066G1", "NVIDIA CORP", 239)]), "426030", date(2026, 11, 6))


def test_fetch_trading_day_retries_empty_then_returns_data(monkeypatch):
    results = [EMPTY, ONE_ROW]
    sleeps = []
    monkeypatch.setattr(etf_holdings, "fetch_holdings", lambda code, d: results.pop(0))
    monkeypatch.setattr(etf_holdings.time, "sleep", sleeps.append)
    assert len(fetch_trading_day("426030", date(2026, 11, 6))) == 1
    assert sleeps == [5]


def test_collect_day_reports_failure_when_still_empty(monkeypatch, capsys):
    calls = []

    def always_empty(code, d):
        calls.append(code)
        return EMPTY

    monkeypatch.setattr(etf_holdings, "fetch_holdings", always_empty)
    monkeypatch.setattr(etf_holdings.time, "sleep", lambda s: None)
    assert collect_day(None, "426030", date(2026, 11, 6)) is None
    assert len(calls) == 3
    assert "수집 실패" in capsys.readouterr().out


class MainConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def commit(self):
        pass


def run_today(monkeypatch, collected):
    """main today 를 DB·KRX 없이 돌린다. collected: ETF 코드 -> collect_day 결과."""
    monkeypatch.setenv("KRX_ID", "id")
    monkeypatch.setenv("KRX_PW", "pw")
    monkeypatch.setattr("db.get_conn", MainConn)
    monkeypatch.setattr(etf_holdings, "latest_trading_day", lambda today: date(2026, 11, 6))
    monkeypatch.setattr(etf_holdings, "collect_day", lambda conn, code, d: collected[code])
    monkeypatch.setattr(etf_holdings, "fill_tickers", lambda conn: 0)
    return main(["today"])


def test_main_exits_with_failure_but_keeps_other_etf(monkeypatch, capsys):
    assert run_today(monkeypatch, {"426030": 41, "0015B0": None}) == 1
    assert "수집 실패 1건: 0015B0 2026-11-06" in capsys.readouterr().out


def test_main_exits_ok_when_snapshot_already_saved(monkeypatch):
    # 다시 돌려 새로 넣은 줄이 0 이어도 받아 온 것이므로 실패가 아니다
    assert run_today(monkeypatch, {"426030": 0, "0015B0": 52}) == 0
