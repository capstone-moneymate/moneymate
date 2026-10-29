from datetime import date

import pandas as pd

from collectors.filings_13f import Report, clean_ticker, merge_reports, shares_by_cusip

COLS = ["Issuer", "Cusip", "SharesPrnAmount", "Type", "PutCall", "Ticker"]


def table(rows):
    return pd.DataFrame(rows, columns=COLS)


def test_shares_by_cusip_filters_and_sums():
    # 드러켄밀러처럼 같은 CUSIP 에 콜옵션 줄이 섞이고, 버크셔처럼 운용 주체별로 여러 줄인 경우
    t = table([
        ["Amazon Com Inc", "023135106", 541600, "Shares", "", "AMZN"],
        ["Amazon Com Inc", "023135106", 459300, "Shares", "Call", "AMZN"],   # P5: 옵션 제외
        ["ALLY FINL INC", "02005N100", 12561737, "Shares", "", "ALLY"],
        ["ALLY FINL INC", "02005n100 ", 2803875, "Shares", "", "ALLY"],      # P14: 합산 (대소문자·공백 정리)
        ["SOME BOND", "123456AB1", 1000000, "Principal", "", ""],            # P5: 채권 제외
    ])
    out = shares_by_cusip(t).set_index("cusip")["shares"].to_dict()
    # 손계산: AMZN 541600, ALLY 12561737 + 2803875 = 15365612
    assert out == {"023135106": 541600, "02005N100": 15365612}


def test_shares_by_cusip_drops_empty_placeholder():
    # 틸 2026-03-31분: 보유가 없어서 CUSIP 000000000, 0주 한 줄만 냄 -> 저장할 행 없음
    t = table([["NA", "000000000", 0, "Shares", "", None]])
    assert shares_by_cusip(t).empty


def test_merge_reports_adds_new_holdings_after_original():
    # 버핏처럼 원본(5/15) 뒤에 기밀 처리 해제로 NEW HOLDINGS(8/14)가 나온 경우: 둘을 더한다
    orig = Report("a1", date(2025, 5, 15), False, None, table([["A", "AAA000001", 100, "Shares", "", "AAA"]]))
    add = Report("a2", date(2025, 8, 14), True, "NEW HOLDINGS", table([["B", "BBB000001", 50, "Shares", "", "BBB"]]))
    out, base = merge_reports([orig, add])
    assert base.accession_no == "a1"
    assert out.set_index("cusip")["shares"].to_dict() == {"AAA000001": 100, "BBB000001": 50}


def test_merge_reports_restatement_replaces_original():
    # RESTATEMENT(6/1)가 원본을 대신하고, 그보다 먼저 낸 NEW HOLDINGS(5/20)는 이미 들어 있다고 본다
    orig = Report("a1", date(2025, 5, 15), False, None, table([["A", "AAA000001", 100, "Shares", "", "AAA"]]))
    add = Report("a2", date(2025, 5, 20), True, "NEW HOLDINGS", table([["B", "BBB000001", 50, "Shares", "", "BBB"]]))
    rest = Report("a3", date(2025, 6, 1), True, "RESTATEMENT", table([["A", "AAA000001", 120, "Shares", "", "AAA"]]))
    out, base = merge_reports([orig, add, rest])
    assert base.accession_no == "a3"
    assert out.set_index("cusip")["shares"].to_dict() == {"AAA000001": 120}


def test_clean_ticker():
    assert clean_ticker("BRK.B") == "BRK-B"
    assert clean_ticker("") is None
    assert clean_ticker(float("nan")) is None
    assert clean_ticker("12345") is None
