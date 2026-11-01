from datetime import date
from decimal import Decimal

import pandas as pd

from collectors.etf_holdings import holdings_from_pykrx, unit_change_ratio


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
