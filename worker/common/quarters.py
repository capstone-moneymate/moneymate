"""13F 분기 말 날짜 계산. 13F 는 3/31, 6/30, 9/30, 12/31 기준이다."""
from datetime import date

_QUARTER_ENDS = ((3, 31), (6, 30), (9, 30), (12, 31))


def is_quarter_end(d: date) -> bool:
    return (d.month, d.day) in _QUARTER_ENDS


def prev_quarter_end(d: date) -> date:
    """d 보다 앞선 가장 가까운 분기 말. 2026-06-30 -> 2026-03-31, 2026-08-14 -> 2026-06-30."""
    for year in (d.year, d.year - 1):
        for month, day in reversed(_QUARTER_ENDS):
            q = date(year, month, day)
            if q < d:
                return q
    raise AssertionError("도달하지 않음")


def latest_quarter_end(d: date) -> date:
    """d 이하의 가장 최근 분기 말. 2026-06-30 -> 2026-06-30, 2026-08-14 -> 2026-06-30."""
    return d if is_quarter_end(d) else prev_quarter_end(d)


def parse_quarter_end(s: str) -> date:
    """'2026-06-30' -> date. 분기 말이 아니면 ValueError."""
    d = date.fromisoformat(s)
    if not is_quarter_end(d):
        raise ValueError(f"분기 말 날짜가 아님: {s} (3/31, 6/30, 9/30, 12/31 중 하나)")
    return d

