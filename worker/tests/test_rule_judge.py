from generate.rule_judge import grade, to_score

CHAIN = [
    {"name": "기준금리 동결", "aliases": ["동결"]},
    {"name": "예대금리차", "aliases": ["이자 마진"]},
    {"name": "은행 실적", "aliases": ["은행 이익"]},
]
FACTS = [
    {"text": "한은 기준금리 3.00% 동결", "keywords": ["3.00%", "3%"]},
    {"text": "4회 연속 동결", "keywords": ["4회 연속", "네 번 연속"]},
]


def test_full_marks():
    text = ("기준금리가 3%로 4회 연속 동결됐기 때문에 예대금리차가 유지되고, 그래서 은행 실적이 좋아질 것 같아 추가매수를 골랐다. "
            "하지만 만약 경기가 나빠지면 대출 연체가 늘어 은행 이익이 줄 수 있다.")
    r = grade(text, FACTS, CHAIN)
    # 증거: 사실 2개(3%, 4회 연속) + 연결어(때문) -> 2
    # 추론: 개념 3개(동결, 예대금리차, 은행 실적) + 연결어 2개 이상(때문, 그래서) -> 4
    # 반박: '하지만' 문장에 다른 힘(은행 이익) + 조건(만약) -> 3
    assert r.rubric == {"evidence": 2, "reasoning": 4, "rebuttal": 3}
    assert r.score == 100


def test_concepts_without_connective():
    r = grade("금리가 동결돼서 은행 실적이 좋아질 것 같다.", FACTS, CHAIN)
    # 증거: 3%·4회 연속 없음 -> 0 / 추론: 개념 2개(동결, 은행 실적), 연결어 없음('돼서'는 목록에 없음) -> 2 / 반박 0
    assert r.rubric == {"evidence": 0, "reasoning": 2, "rebuttal": 0}
    assert r.score == 22   # 2/9*100 = 22.2


def test_facts_without_connective_is_1():
    r = grade("3% 동결, 4회 연속.", FACTS, CHAIN)
    # 증거: 사실 2개지만 연결어 없음 -> 1 / 추론: 개념 1개(동결) -> 1
    assert r.rubric == {"evidence": 1, "reasoning": 1, "rebuttal": 0}


def test_contrast_only_is_1():
    r = grade("좋아 보인다. 다만 잘 모르겠다.", FACTS, CHAIN)
    assert r.rubric == {"evidence": 0, "reasoning": 0, "rebuttal": 1}


def test_empty_answer():
    r = grade("그냥 좋아 보여서 샀다.", FACTS, CHAIN)
    assert r.total == 0 and r.score == 0


def test_spacing_ignored():
    # '기준 금리 동결' 처럼 띄어 써도 개념 이름과 맞춘다
    assert grade("기준 금리 동결", FACTS, CHAIN).matched_concepts == ["기준금리 동결"]


def test_to_score_rounding():
    assert to_score(6) == 67   # 66.67 -> 67 (60점 이상이면 맞음, conventions P17)
    assert to_score(5) == 56   # 55.56
    assert to_score(9) == 100
    assert to_score(12) == 100  # 범위 밖은 자른다
