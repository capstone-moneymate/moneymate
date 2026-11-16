"""scripts/check_13f_quarter.py 의 순수 함수. 손계산 예시가 정답."""
import pandas as pd

from scripts.check_13f_quarter import drop_note, raw_counts, top_bottom


def test_drop_note_flags_half_or_more_and_zero():
    assert drop_note(86, 43) == "급감: 86 → 43 (-50%)"   # 정확히 절반 줄면 급감
    assert drop_note(86, 44) is None                      # 절반보다 덜 줄면 아님
    assert drop_note(8, 0) == "급감: 종목 0개 (빈 13F 이거나 수집 누락)"
    assert drop_note(0, 8) is None                        # 직전이 빈 13F(틸 3/31)면 비교 안 함
    assert drop_note(29, 35) is None


def _row(ticker, pct, cusip="000000000"):
    return {"ticker": ticker, "cusip": cusip, "chg_pct": pct}


def test_top_bottom_skips_null_and_sorts():
    rows = [_row("A", 0.2), _row("B", None), _row("C", -1.0), _row("D", 0.5), _row("E", -0.25),
            _row(None, 0.2, cusip="123456789")]
    top, bottom = top_bottom(rows, n=3)
    assert [r["ticker"] or r["cusip"] for r in top] == ["D", "123456789", "A"]   # 같은 0.2 는 이름 순(숫자 먼저)
    assert [r["ticker"] or r["cusip"] for r in bottom] == ["C", "E", "123456789"]


def test_raw_counts_matches_collector_filter():
    t = pd.DataFrame({
        "Type": ["Shares", "Shares", "Principal", "Shares"],
        "PutCall": [None, "Put", None, " "],
    })
    assert raw_counts(t) == {"전체": 4, "옵션(PUT/CALL)": 1, "채권 등(Shares 아님)": 1}
