"""validators.find_banned 테스트. banned_terms.txt 실제 목록으로 돌린다."""
import re

import pytest

from validate.validators import find_banned, parse_banned

# C의 compose.py FORBIDDEN 정규식 (feat/compose-44, 2026-11-01). 옮긴 목록이 이것과 똑같이 걸러야 한다
C_FORBIDDEN = re.compile(
    r"매수\s*(?:추천|하세요|하라|타이밍)|매도\s*(?:추천|하세요|하라|타이밍)|사세요|파세요|팔아라|사라\b|담으세요|담아라"
    r"|추천\s*종목|목표\s*(?:주)?가|오를\s*것|내릴\s*것|떨어질\s*것|상승할\s*(?:것|전망)|하락할\s*(?:것|전망)"
    r"|수익(?:이|을)?\s*(?:기대|보장)|반드시\s*오"
)


@pytest.mark.parametrize("text, hit", [
    ("지금이 매수 타이밍이에요", "매수 타이밍"),
    ("오늘의 매수추천", "매수추천"),              # 띄어쓰기 없어도
    ("이 종목은 꼭 사세요", "사세요"),
    ("이번 주에 팔아라", "팔아라"),
    ("증권사 목표주가는 15만 원", "목표주가"),
    ("목표가를 올렸다", "목표가"),
    ("주가가 오를 것으로 보여요", "오를 것"),
    ("하반기에 상승할 전망", "상승할 전망"),
    ("수익을 기대할 수 있어요", "수익을 기대"),
    ("반드시 오릅니다", "반드시 오"),
    ("지금 사라.", "사라"),
])
def test_find_banned_hits(text, hit):
    assert find_banned([text]) == [hit]


@pytest.mark.parametrize("text", [
    "외국인 매수세가 몰렸다",             # '매수' 만으로는 걸지 않는다
    "기관이 순매도했다",
    "올해 목표 달성률은 80%예요",
    "공장 투자가 사라진 이유",            # 사라\b: 단어 중간은 걸지 않음
    "기준금리를 동결했어요. 시장은 인하 기대를 낮췄어요.",
    "수익률은 4.6%였어요",
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


SAMPLES = [
    "지금이 매수 타이밍", "매도하세요", "매수세", "꼭 사세요", "파세요", "팔아라", "사라", "사라진", "사라고",
    "담으세요", "담아라", "추천 종목", "추천종목", "목표가", "목표 주가", "목표 달성", "오를 것", "오를것",
    "내릴 것", "떨어질 것", "상승할 것", "상승할 전망", "하락할 전망", "하락세", "수익 기대", "수익이 보장",
    "수익률", "반드시 오른다", "반드시 확인", "기준금리 동결", "",
]


@pytest.mark.parametrize("text", SAMPLES)
def test_same_as_c_forbidden(text):
    # 옮긴 목록이 C의 정규식과 같은 문장을 거르는지 (걸렸는지 여부 비교)
    assert bool(find_banned([text])) == bool(C_FORBIDDEN.search(text))
