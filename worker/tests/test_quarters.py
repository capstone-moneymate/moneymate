from datetime import date

import pytest

from common.quarters import latest_quarter_end, parse_quarter_end, prev_quarter_end


def test_prev_quarter_end():
    assert prev_quarter_end(date(2026, 6, 30)) == date(2026, 3, 31)
    assert prev_quarter_end(date(2026, 3, 31)) == date(2025, 12, 31)   # 해가 바뀜
    assert prev_quarter_end(date(2026, 1, 15)) == date(2025, 12, 31)
    assert prev_quarter_end(date(2026, 8, 14)) == date(2026, 6, 30)    # 2분기 13F 공시일


def test_latest_quarter_end():
    assert latest_quarter_end(date(2026, 6, 30)) == date(2026, 6, 30)
    assert latest_quarter_end(date(2026, 8, 14)) == date(2026, 6, 30)


def test_parse_quarter_end_rejects_other_days():
    assert parse_quarter_end("2026-09-30") == date(2026, 9, 30)
    with pytest.raises(ValueError):
        parse_quarter_end("2026-06-29")
