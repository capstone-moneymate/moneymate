"""sources.py 의 변환 함수 (네트워크 없이). DART·ECOS 응답 모양은 각 API 문서의 예시를 따른 가짜 값이다."""
from datetime import date

import pytest

from collectors.sources import (
    MACRO_CALENDAR,
    bok_rate_change,
    dart_rows_to_sources,
    ecos_rows,
    fed_rate_change,
    load_macro_calendar,
    macro_sources_on,
)


def _dart(rcept_no, corp_cls, stock_code, report_nm, corp_name="테스트전자"):
    return {"rcept_no": rcept_no, "corp_cls": corp_cls, "stock_code": stock_code, "corp_name": corp_name,
            "report_nm": report_nm, "rcept_dt": "20261027"}


def test_dart_rows_filter_and_convert():
    rows = [
        _dart("20261027000001", "Y", "5930", "단일판매ㆍ공급계약체결"),
        _dart("20261027000002", "K", "091990", "[기재정정]단일판매ㆍ공급계약체결"),   # 정정 → 제외
        _dart("20261027000003", "N", "123456", "영업(잠정)실적(공정공시)"),          # 코넥스 → 제외
        _dart("20261027000004", "E", " ", "자기주식취득결정"),                      # 비상장 → 제외
        _dart("20261027000005", "K", "091990", "임원ㆍ주요주주특정증권등소유상황보고서"),
    ]
    out = dart_rows_to_sources(rows)
    assert len(out) == 1
    s = out[0]
    assert (s.ticker, s.market, s.category) == ("005930", "KR", "supply_contract")
    assert s.published_date == date(2026, 10, 27)
    assert s.published_at is None  # DART 는 시각을 주지 않는다
    assert s.url.endswith("rcpNo=20261027000001")


def test_macro_calendar_file_and_lookup():
    cal = load_macro_calendar(MACRO_CALENDAR)
    assert {r["kind"] for r in cal} == {"fomc", "bok_rate"}
    # FOMC 10/28 14:00 EDT. 날짜는 미국 현지 날짜로 맞춘다
    out = macro_sources_on(date(2026, 10, 28), cal)
    assert [s.source_key for s in out] == ["fomc_2026_10"]
    assert out[0].ticker == "US500" and out[0].published_at.utcoffset().total_seconds() == -4 * 3600
    assert out[0].numbers["calendar_verified"] is True


def test_bok_rate_change_hold_and_cut():
    rows = [{"TIME": "20261020", "DATA_VALUE": "2.5"}, {"TIME": "20261021", "DATA_VALUE": "2.5"},
            {"TIME": "20261022", "DATA_VALUE": "2.5"}]
    assert bok_rate_change(rows, date(2026, 10, 22)) == {"rate_before": 2.5, "rate_after": 2.5, "decision": "hold"}
    rows[-1]["DATA_VALUE"] = "2.25"
    assert bok_rate_change(rows, date(2026, 10, 22))["decision"] == "cut"
    assert bok_rate_change(rows[:1], date(2026, 10, 20)) is None  # 결정일 전 값이 없음


def test_ecos_rows_error_payload():
    # 실제 ECOS 응답 모양 (2026-10-28): 오류는 RESULT 로 온다
    assert ecos_rows({"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}) == []
    with pytest.raises(RuntimeError, match="INFO-100"):
        ecos_rows({"RESULT": {"CODE": "INFO-100", "MESSAGE": "인증키가 유효하지 않습니다."}})
    rows = [{"TIME": "20261022", "DATA_VALUE": "3"}]
    assert ecos_rows({"StatisticSearch": {"list_total_count": 1, "row": rows}}) == rows


def test_fed_rate_change_uses_next_day():
    # FRED 는 결정 다음 날부터 새 목표가 찍힌다. 9/16 결정 → 9/17 3.75 → 4.00
    series = [(date(2026, 9, 15), 3.75), (date(2026, 9, 16), 3.75), (date(2026, 9, 17), 4.0)]
    assert fed_rate_change(series, date(2026, 9, 16)) == {"rate_before": 3.75, "rate_after": 4.0, "decision": "hike"}
    # 한은처럼 당일 값을 보면 3.75 → 3.75 동결로 잘못 판정된다
    assert bok_rate_change([{"TIME": t.strftime("%Y%m%d"), "DATA_VALUE": str(v)} for t, v in series],
                           date(2026, 9, 16))["decision"] == "hold"
    # 다음 날 값이 아직 없으면 판정하지 않는다
    assert fed_rate_change(series[:2], date(2026, 9, 16)) is None
