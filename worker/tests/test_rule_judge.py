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
COUNTER = [{"name": "경기 둔화", "aliases": ["연체"]}]


def test_full_marks():
    text = ("기준금리가 3%로 4회 연속 동결됐기 때문에 예대금리차가 유지되고, 그래서 은행 실적이 좋아질 것 같아 추가매수를 골랐다. "
            "금리가 계속 동결되는 경우라면 다른 은행주에도 같은 흐름이 이어질 수 있다. "
            "하지만 경기 둔화로 연체가 늘면 은행 이익이 줄 수 있다.")
    r = grade(text, FACTS, CHAIN, COUNTER)
    # 증거: 사실 2개(3%, 4회 연속) + 연결어(때문) -> 2
    # 추론: 개념 3개 + 연결어, 반박이 아닌 2번째 문장에서 '경우라면'으로 일반화 -> 4 (확장된 추상)
    # 반박: '하지만' 뒤 요인 2개(경기 둔화, 은행 실적의 다른 이름 '은행 이익') -> 3
    assert r.rubric == {"evidence": 2, "reasoning": 4, "rebuttal": 3}
    assert r.score == 100


def test_relational_is_3_when_condition_only_in_rebuttal():
    text = "동결 때문에 예대금리차가 커진다. 하지만 만약 경기가 나빠지면 은행 이익이 준다."
    r = grade(text, FACTS, CHAIN)
    # 추론: 개념 3개 + 연결어(때문)지만 '만약'은 반박 문장에만 있음 -> 3 (관계적)
    # 반박: '하지만' 뒤 요인 1개(은행 이익) -> 2
    assert r.rubric == {"evidence": 0, "reasoning": 3, "rebuttal": 2}


def test_plain_causal_if_is_not_generalization():
    # '동결되면'은 평범한 인과라 일반화(4)로 보지 않는다
    r = grade("동결되면 예대금리차가 커지고 그래서 은행 실적이 오른다.", FACTS, CHAIN)
    assert r.rubric["reasoning"] == 3


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
    # 반박: 반대 표현만 있고 요인이 없음 -> 1 (위험을 언급했지만 연결이 약함)
    assert r.rubric == {"evidence": 0, "reasoning": 0, "rebuttal": 1}


def test_same_factor_twice_counts_once():
    # 같은 개념을 이름·다른 이름으로 두 번 써도 요인 1개 -> 2
    r = grade("다만 은행 실적이 줄 수 있다. 하지만 은행 이익도 모른다.", FACTS, CHAIN)
    assert r.rubric["rebuttal"] == 2


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
