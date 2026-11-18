from datetime import date
from types import SimpleNamespace

import pandas as pd

from collectors.filings_13f import (
    Report, clean_ticker, merge_reports, pick_ticker, select_filings, shares_by_cusip,
)

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


def filing(acc, form, period="2026-09-30"):
    return SimpleNamespace(accession_no=acc, form=form, period_of_report=period)


def test_select_filings_keeps_period_and_drops_duplicate_accession():
    # get_filings 가 정정 신고(a2)를 13F-HR 목록과 13F-HR/A 목록에 두 번 돌려줘도 한 번만 남는다
    fs = [filing("a1", "13F-HR"), filing("a2", "13F-HR/A"), filing("a0", "13F-HR", "2026-06-30"),
          filing("a2", "13F-HR/A")]
    out = select_filings(fs, date(2026, 9, 30))
    assert [(f.accession_no, f.form) for f in out] == [("a1", "13F-HR"), ("a2", "13F-HR/A")]


def test_late_new_holdings_amendment_does_not_replace_original():
    # 13F 버그 재현: 원본(11/14, 2종목) 뒤에 NEW HOLDINGS 정정(11/20, 1종목)이 나온 분기.
    # 예전처럼 정정을 원본(is_amendment=False)으로 넣으면 늦은 쪽이 대표가 되어 원본 2종목이 사라졌다
    orig = table([["A", "AAA000001", 100, "Shares", "", "AAA"], ["B", "BBB000001", 40, "Shares", "", "BBB"]])
    add = table([["C", "CCC000001", 50, "Shares", "", "CCC"]])
    wrong, base = merge_reports([Report("a1", date(2026, 11, 14), False, None, orig),
                                 Report("a2", date(2026, 11, 20), False, None, add)])
    assert base.accession_no == "a2" and set(wrong["cusip"]) == {"CCC000001"}   # 예전 결과 (틀림)
    # f.form 으로 가르면 정정은 원본에 더해진다: 100 + 40 + 50 세 종목, 대표는 원본
    out, base = merge_reports([Report("a1", date(2026, 11, 14), False, None, orig),
                               Report("a2", date(2026, 11, 20), True, "NEW HOLDINGS", add)])
    assert base.accession_no == "a1"
    assert out.set_index("cusip")["shares"].to_dict() == {"AAA000001": 100, "BBB000001": 40, "CCC000001": 50}


def test_clean_ticker():
    assert clean_ticker("BRK.B") == "BRK-B"
    assert clean_ticker("") is None
    assert clean_ticker(float("nan")) is None
    assert clean_ticker("12345") is None


def test_pick_ticker_prefers_openfigi():
    # #99: SEC 원본 'LENB'(Lennar B주)는 하이픈이 없어 정규화로 못 고친다. OpenFIGI 'LEN-B' 를 쓴다
    assert pick_ticker("LENB", "LEN-B") == ("LEN-B", "openfigi")
    assert pick_ticker("NVDA", "NVDA") == ("NVDA", "openfigi")
    # OpenFIGI 에 없는 해외 등록 CUSIP(Linde G54950103 등)은 edgartools 값
    assert pick_ticker("LIN", None) == ("LIN", "edgartools")
    assert pick_ticker("BRK.B", None) == ("BRK-B", "edgartools")
    # 둘 다 없으면 NULL
    assert pick_ticker(None, None) == (None, "openfigi")
    assert pick_ticker("12345", None) == (None, "openfigi")
