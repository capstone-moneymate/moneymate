"""validators.find_duplicates 테스트. 점수는 RapidFuzz ratio + default_process 로 직접 재 본 값이다 (2026-11-02)."""
from validate.validators import find_duplicates

PAST = [
    "NVDA 차트에서 10월 중 거래량이 가장 많았던 날은 언제일까요?",
    "한국은행이 기준금리를 동결하면 성장주 가치평가에는 어떤 압력이 생길까요?",
]


def test_same_question_is_duplicate():
    out = find_duplicates(["NVDA 차트에서 10월 중 거래량이 가장 많았던 날은 언제일까요?"], PAST)
    assert len(out) == 1 and "유사도 100" in out[0]


def test_punctuation_and_spacing_ignored():
    # 물음표·마침표만 다른 경우도 거의 같은 문장
    out = find_duplicates(["NVDA 차트에서 10월 중 거래량이 가장 많았던 날은 언제일까요."], PAST)
    assert len(out) == 1


def test_same_template_other_ticker_passes():
    # 같은 틀에 종목만 바뀜: ratio 86 < 90
    assert find_duplicates(["005930 차트에서 10월 중 거래량이 가장 많았던 날은 언제일까요?"], PAST) == []


def test_same_template_other_event_passes():
    # 같은 틀에 사건만 바뀜: ratio 86 < 90
    assert find_duplicates(["미국 연준이 기준금리를 인하하면 성장주 가치평가에는 어떤 압력이 생길까요?"], PAST) == []


def test_short_question_inside_long_one_passes():
    # token_set_ratio 였다면 100. ratio 는 56
    assert find_duplicates(["거래량이 가장 많았던 날은?"], PAST) == []


def test_different_question_passes():
    assert find_duplicates(["RSI가 70을 넘었다는 것은 무엇을 뜻할까요?"], PAST) == []


def test_threshold_is_adjustable():
    # 기준을 낮추면 같은 틀 다른 종목(86)도 걸린다
    assert len(find_duplicates(["005930 차트에서 10월 중 거래량이 가장 많았던 날은 언제일까요?"], PAST, threshold=85)) == 1


def test_empty_inputs():
    assert find_duplicates([], PAST) == []
    assert find_duplicates(["무엇이든"], []) == []
    assert find_duplicates(["", "  "], PAST) == []
    assert find_duplicates(["NVDA 차트에서 10월 중 거래량이 가장 많았던 날은 언제일까요?"], ["", None]) == []


def test_reports_each_duplicate():
    out = find_duplicates([PAST[0], "RSI가 70을 넘었다는 것은?", PAST[1]], PAST)
    assert len(out) == 2
