"""validators.find_banned 테스트. banned_terms.txt 실제 목록으로 돌린다."""
import pytest

from validate.validators import find_banned, parse_banned


@pytest.mark.parametrize("text, hit", [
    ("지금이 매수 타이밍이에요", "매수 타이밍"),
    ("오늘의 매수추천", "매수추천"),              # 띄어쓰기 없어도
    ("이 종목은 꼭 사세요", "사세요"),
    ("이번 주에 팔아라", "팔아라"),
    ("증권사 목표주가는 15만 원", "목표주가"),
    ("목표가를 올렸다", "목표가를"),
    ("목표가 15만 원", "목표가 15만 원"),
    ("증권사 목표가 상향", "목표가 상향"),
    ("주가가 오를 것으로 보여요", "오를 것"),
    ("하반기에 상승할 전망", "상승할 전망"),
    ("수익을 기대할 수 있어요", "수익을 기대"),
    ("반드시 오릅니다", "반드시 오릅"),
    ("반드시 올라요", "반드시 올라"),
    ("지금 사라.", "지금 사라"),
    ("이 주식을 사라.", "을 사라"),
])
def test_find_banned_hits(text, hit):
    assert find_banned([text]) == [hit]


@pytest.mark.parametrize("text", [
    "매도하세요", "꼭 사세요", "파세요", "담으세요", "담아라", "추천 종목", "추천종목", "오를것",
    "내릴 것", "떨어질 것", "상승할 것", "하락할 전망", "수익 기대", "수익이 보장",
])
def test_find_banned_other_terms(text):
    assert find_banned([text])


@pytest.mark.parametrize("text", [
    "외국인 매수세가 몰렸다",             # '매수' 만으로는 걸지 않는다
    "기관이 순매도했다",
    "올해 목표 달성률은 80%예요",
    "공장 투자가 사라진 이유",            # 사라\b: 단어 중간은 걸지 않음
    "기준금리를 동결했어요. 시장은 인하 기대를 낮췄어요.",
    "수익률은 4.6%였어요",
    "메모리를 만드는 회사라.",            # 사라: 앞말의 끝 글자
    "오픈AI CFO 사라 프라이어가 말했다.",  # 사라: 사람 이름
    "한국은행의 목표가 물가 안정이에요.",  # 목표 + 조사 '가'
    "물가 목표가 2%예요.",                # 목표가 뒤 숫자여도 주가가 아님
    "반드시 오늘 발표를 확인해 보세요.",
    "반드시 올해 안에 확인해 보세요.",
    "사라고", "하락세", "반드시 확인",
    "",
])
def test_find_banned_allows_normal_sentences(text):
    assert find_banned([text]) == []


def test_find_banned_collects_across_texts_without_repeats():
    texts = ["제목: 매수 추천", "해설: 오를 것", "보기: 매수 추천"]
    assert find_banned(texts) == ["매수 추천", "오를 것"]


def test_parse_banned_skips_comments_and_makes_spaces_optional():
    patterns = parse_banned(["# 주석", "", "  추천 종목  "])
    assert len(patterns) == 1
    assert patterns[0].search("추천종목") and patterns[0].search("추천   종목")
