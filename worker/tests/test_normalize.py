import pytest

from common.normalize import normalize_kr_code, normalize_us_ticker


def test_us_ticker_basic():
    assert normalize_us_ticker(" nvda ") == "NVDA"


def test_us_ticker_class_share():
    assert normalize_us_ticker("brk.b") == "BRK-B"
    assert normalize_us_ticker("BRK-B") == "BRK-B"


def test_us_ticker_invalid():
    with pytest.raises(ValueError):
        normalize_us_ticker("삼성전자")


def test_kr_code_keeps_leading_zero():
    assert normalize_kr_code(5930) == "005930"
    assert normalize_kr_code("426030") == "426030"


def test_kr_code_invalid():
    with pytest.raises(ValueError):
        normalize_kr_code("ABC")


def test_kr_code_with_letters():
    # KoAct ETF, 우선주처럼 영문 대문자가 섞인 6자리 코드
    assert normalize_kr_code("0015B0") == "0015B0"
    assert normalize_kr_code(" 00104k ") == "00104K"


def test_kr_code_with_letters_must_be_6_chars():
    # 영문이 섞이면 0을 채우지 않는다
    with pytest.raises(ValueError):
        normalize_kr_code("15B0")
    with pytest.raises(ValueError):
        normalize_kr_code("0015B00")


def test_kr_code_letters_only_invalid():
    with pytest.raises(ValueError):
        normalize_kr_code("ABCDEF")
