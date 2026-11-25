"""튜터 퀴즈 7종류: 찍어서 맞힐 확률 손계산, 모양 검사, 채점, 출제 재시도. 실제 API 는 부르지 않는다."""
import json
from types import SimpleNamespace

import pytest

from tutor import quiz as qz

# 용어 뜻 출제 응답: 보기는 칸 3개 (#246). to_quiz 가 [correct, wrong_1, wrong_2] 순서, 정답 0 으로 만든다
CHOICE = {"question": "EPS 의 뜻은?", "correct": "주당순이익", "wrong_1": "주가수익비율", "wrong_2": "자기자본",
          "explanation": "순이익을 주식 수로 나눈 값"}
OPTIONS = ["주당순이익", "주가수익비율", "자기자본"]
PAIR = {"question": "EPS 는?", "options": ["주당순이익", "주당순자산"], "answer_index": 1, "explanation": "e"}


def test_guess_probability_by_hand():
    assert qz.guess_probability("용어 뜻", {"options": [1, 2, 3]}) == pytest.approx(1 / 3)
    assert qz.guess_probability("헷갈리는 쌍", {"options": [1, 2]}) == 0.5
    assert qz.guess_probability("O/X", {}) == 0.5
    # 칩 4개에서 빈칸 2개를 순서대로: 4 × 3 = 12 가지 → 약 8%
    assert qz.guess_probability("칩 빈칸", {"chips": list("abcd"), "sentence": "___ 와 ___"}) == pytest.approx(1 / 12)
    # 짝 3쌍: 3! = 6 가지 → 약 17%
    assert qz.guess_probability("짝 맞추기", {"terms": [1, 2, 3]}) == pytest.approx(1 / 6)
    # 사례 4개를 바구니 2개에: 2⁴ = 16 가지 → 약 6%
    assert qz.guess_probability("사례 분류", {"baskets": [1, 2], "cases": [1, 2, 3, 4]}) == pytest.approx(1 / 16)


def test_choice_quiz_ok_and_hides_key():
    q = qz.to_quiz("용어 뜻", "주당순이익", CHOICE)
    assert q.content == {"question": "EPS 의 뜻은?", "options": OPTIONS}
    assert q.key == 0 and "answer_index" not in q.content
    assert qz.grade(q, 0) and not qz.grade(q, 1)


@pytest.mark.parametrize("change, msg", [
    ({"wrong_1": "주당순이익"}, "같은 보기"),
    ({"wrong_2": " "}, "빈 보기"),
    ({"explanation": "지금 매수 추천"}, "금지 표현"),
])
def test_choice_quiz_errors(change, msg):
    with pytest.raises(qz.QuizError, match=msg):
        qz.to_quiz("용어 뜻", "주당순이익", CHOICE | change)


def test_confusable_pair_must_use_both_names():
    pair = ["주당순이익", "주당순자산"]
    assert qz.to_quiz("헷갈리는 쌍", "주당순이익", PAIR, pair=pair).key == 1
    with pytest.raises(qz.QuizError, match="두 개념 이름"):
        qz.to_quiz("헷갈리는 쌍", "주당순이익", PAIR | {"options": ["EPS", "BPS"]}, pair=pair)
    with pytest.raises(qz.QuizError, match="보기가 2개"):
        qz.to_quiz("헷갈리는 쌍", "주당순이익", PAIR | {"options": pair + ["EPS"]}, pair=pair)
    with pytest.raises(qz.QuizError, match="범위 밖"):
        qz.to_quiz("헷갈리는 쌍", "주당순이익", PAIR | {"answer_index": 2}, pair=pair)


def test_wrong_statement_slots():
    """틀린 설명은 맞는 설명 2칸 + 틀린 설명 1칸. 틀린 설명이 정답이고 보기는 늘 3개 (#246)"""
    data = {"question": "틀린 것은?", "true_1": "가", "true_2": "나", "wrong": "다", "explanation": "e"}
    q = qz.to_quiz("틀린 설명", "주당순이익", data)
    assert q.content == {"question": "틀린 것은?", "options": ["가", "나", "다"]} and q.key == 2
    assert q.guess_p == pytest.approx(1 / 3)
    with pytest.raises(qz.QuizError, match="같은 보기"):
        qz.to_quiz("틀린 설명", "주당순이익", data | {"wrong": "가"})
    schema = qz._schema_for("틀린 설명")
    assert "options" not in schema["properties"] and schema["required"] == ["question", "true_1", "true_2", "wrong", "explanation"]


def test_ox_chips_match_classify():
    ox = qz.to_quiz("O/X", "자사주 소각", {"statement": "소각하면 주식 수가 준다", "answer": True, "explanation": "e"})
    assert ox.content["options"] == ["O", "X"] and ox.key == 0

    chips = {"sentence": "회사가 ___ 를 사서 ___ 하면 주식 수가 준다", "chips": ["자사주", "소각", "배당", "증자"],
             "answers": ["자사주", "소각"], "explanation": "e"}
    q = qz.to_quiz("칩 빈칸", "자사주 소각", chips)
    assert q.key == [0, 1] and qz.grade(q, [0, 1]) and not qz.grade(q, [1, 0])
    with pytest.raises(qz.QuizError, match="빈칸"):
        qz.to_quiz("칩 빈칸", "자사주 소각", chips | {"sentence": "___ 하나뿐"})
    with pytest.raises(qz.QuizError, match="정답 칩"):
        qz.to_quiz("칩 빈칸", "자사주 소각", chips | {"answers": ["자사주", "자사주"]})
    # 1부터 센 번호나 칩에 없는 말은 받지 않는다 (#231: Haiku 가 번호를 1부터 셌다)
    for bad in (["1", "2"], ["자사주", "합병"]):
        with pytest.raises(qz.QuizError, match="정답 칩"):
            qz.to_quiz("칩 빈칸", "자사주 소각", chips | {"answers": bad})
    assert qz.to_quiz("칩 빈칸", "자사주 소각", chips | {"answers": ["소각", "배당"]}).key == [1, 2]
    assert qz.to_quiz("칩 빈칸", "자사주 소각", chips | {"answers": ["자 사주", "소각 "]}).key == [0, 1]   # 띄어쓰기 무시

    m = qz.to_quiz("짝 맞추기", "주당순이익", {"meanings": ["가", "나", "다"], "explanation": "e"},
                   terms=["주당순이익", "순이익", "유통 주식 수"])
    assert m.key == [0, 1, 2] and m.content["terms"][0] == "주당순이익"
    with pytest.raises(qz.QuizError, match="용어 수"):
        qz.to_quiz("짝 맞추기", "주당순이익", {"meanings": ["가"], "explanation": "e"}, terms=["a", "b", "c"])

    cls = {"baskets": ["해당", "해당 안 함"], "explanation": "e",
           "cases": [{"text": t, "basket": b} for t, b in [("가", 0), ("나", 1), ("다", 0), ("라", 1)]]}
    assert qz.to_quiz("사례 분류", "자사주 소각", cls).key == [0, 1, 0, 1]
    one_side = cls | {"cases": [{"text": t, "basket": 0} for t in "가나다라"]}
    with pytest.raises(qz.QuizError, match="한쪽만"):
        qz.to_quiz("사례 분류", "자사주 소각", one_side)


def _fake(monkeypatch, *payloads):
    queue, calls = list(payloads), []

    def create(module, **kw):
        calls.append({"module": module, **kw})
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(queue.pop(0)))])

    monkeypatch.setattr(qz, "create", create)
    monkeypatch.setattr(qz, "check", lambda q, desc, card_id=None: [])   # 내용 검사는 따로 본다 (아래)
    return calls


def test_generate_retries_bad_shape_then_ok(monkeypatch):
    calls = _fake(monkeypatch, CHOICE | {"wrong_1": "주당순이익"}, CHOICE)
    q = qz.generate("용어 뜻", "주당순이익", "순이익 ÷ 주식 수")
    assert q.content["options"][q.key] == "주당순이익" and len(calls) == 2 and calls[0]["module"] == "tutor_quiz"
    assert '"desc": "순이익 ÷ 주식 수"' in calls[0]["messages"][0]["content"]


def test_generate_gives_up(monkeypatch):
    _fake(monkeypatch, *[CHOICE | {"wrong_1": "주당순이익"}] * 3)
    with pytest.raises(qz.QuizError, match="같은 보기"):
        qz.generate("용어 뜻", "주당순이익", "")
    with pytest.raises(qz.QuizError, match="모르는"):
        qz.generate("없는 종류", "주당순이익", "")


# --- 정답 위치 섞기 (#231) ---

def _chips():
    return qz.to_quiz("칩 빈칸", "자사주 소각", {"sentence": "회사가 ___ 를 사서 ___ 하면", "explanation": "e",
                                              "chips": ["자사주", "소각", "배당", "증자"], "answers": ["자사주", "소각"]})


def test_shuffle_keeps_answer_text():
    import random
    rng = random.Random(1)
    for _ in range(20):
        q = qz.shuffle(qz.to_quiz("용어 뜻", "주당순이익", CHOICE), rng)
        assert q.content["options"][q.key] == "주당순이익" and sorted(q.content["options"]) == sorted(OPTIONS)
        c = qz.shuffle(_chips(), rng)
        assert [c.content["chips"][k] for k in c.key] == ["자사주", "소각"] and c.guess_p == _chips().guess_p
    cls = {"baskets": ["해당", "해당 안 함"], "explanation": "e",
           "cases": [{"text": x, "basket": b} for x, b in [("가", 0), ("나", 1), ("다", 0), ("라", 1)]]}
    s = qz.shuffle(qz.to_quiz("사례 분류", "자사주 소각", cls), random.Random(3))
    assert dict(zip(s.content["cases"], s.key)) == {"가": 0, "나": 1, "다": 0, "라": 1}
    ox = qz.to_quiz("O/X", "자사주 소각", {"statement": "s", "answer": False, "explanation": "e"})
    assert qz.shuffle(ox, rng) == ox                      # O/X 는 늘 O, X


def test_shuffle_spreads_answer_position():
    # LLM 이 정답을 늘 0번에 두어도 섞은 뒤에는 세 자리에 고루 간다 (300번 중 자리마다 70번 넘게)
    import random
    rng = random.Random(0)
    pos = [qz.shuffle(qz.to_quiz("용어 뜻", "주당순이익", CHOICE), rng).key for _ in range(300)]
    assert all(pos.count(k) > 70 for k in range(3))


def test_generate_shuffles(monkeypatch):
    import random
    _fake(monkeypatch, *[CHOICE] * 30)
    keys = {qz.generate("용어 뜻", "주당순이익", "", rng=random.Random(i)).key for i in range(30)}
    assert keys == {0, 1, 2}


# --- 내용 검사 (#234) ---

def test_claims_by_kind():
    c = _chips()   # 해설 "e"
    cl = qz.claims(c)
    assert cl[0] == ("회사가 [자사주] 를 사서 [소각] 하면", True) and cl[-1] == ("해설: e", True)
    body = cl[1:-1]
    assert len(body) == 11 and not any(ok for _, ok in body)            # 4 × 3 = 12 가지 중 정답 1개 빼고 모두 거짓
    assert ("회사가 [소각] 를 사서 [자사주] 하면", False) in body           # 정답 두 칩을 바꿔 넣은 것 (#237 리뷰)
    assert ("회사가 [배당] 를 사서 [증자] 하면", False) in body
    q = qz.to_quiz("용어 뜻", "주당순이익", CHOICE)
    assert qz.claims(q) == [("'주당순이익'의 뜻: 주당순이익", True), ("'주당순이익'의 뜻: 주가수익비율", False),
                            ("'주당순이익'의 뜻: 자기자본", False), ("해설: 순이익을 주식 수로 나눈 값", True)]
    wrong = qz.to_quiz("틀린 설명", "주당순이익", {"question": "q", "true_1": "가", "true_2": "나", "wrong": "다",
                                               "explanation": " "})
    assert [ok for _, ok in qz.claims(wrong)] == [True, True, False]   # 빈 해설은 넣지 않는다
    cls = {"baskets": ["기업", "상장기업"], "explanation": "",
           "cases": [{"text": x, "basket": b} for x, b in [("가", 0), ("나", 1), ("다", 0), ("라", 1)]]}
    got = qz.claims(qz.to_quiz("사례 분류", "자사주 소각", cls))
    assert got[:4] == [("'가' → 기업", True), ("'가' → 상장기업", False), ("'나' → 기업", False), ("'나' → 상장기업", True)]
    assert len(got) == 8                                                # 사례마다 두 바구니 (#237 리뷰)


def _judge(monkeypatch, judges, advice=False):
    """검사 호출 가짜: 문장 번호 순서대로 judges 를 답한다. 보낸 글도 남긴다."""
    sent = []

    def create(module, **kw):
        sent.append(kw["messages"][0]["content"])
        items = [{"no": i + 1, "reason": "r", "judge": j} for i, j in enumerate(judges)]
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps({"items": items, "advice": advice}))])

    monkeypatch.setattr(qz, "create", create)
    return sent


def test_check_compares_each_statement(monkeypatch):
    q = qz.to_quiz("용어 뜻", "주당순이익", CHOICE | {"explanation": ""})
    sent = _judge(monkeypatch, ["참", "거짓", "거짓"])
    assert qz.check(q, "순이익 ÷ 주식 수") == []
    assert "answer" not in sent[0] and "참" not in sent[0].split("</check>")[0].split("statements")[1]   # 정답은 안 보여 준다
    _judge(monkeypatch, ["참", "참", "거짓"])        # 오답 보기도 참이라 함 → 정답이 둘
    assert len(qz.check(q, "")) == 1
    _judge(monkeypatch, ["애매", "거짓", "거짓"])     # 참이어야 할 문장이 애매면 탈락
    assert "애매" in qz.check(q, "")[0]
    _judge(monkeypatch, ["참", "애매", "거짓"])       # 거짓이어야 할 문장이 애매(말이 안 됨)면 통과: 학습자에게도 오답
    assert qz.check(q, "") == []
    _judge(monkeypatch, ["참", "거짓", "거짓"], advice=True)
    assert qz.check(q, "") == ["매수·매도 권유나 주가 예측이 있어요"]
    _judge(monkeypatch, ["참", "거짓"])               # 문장 하나를 빼먹음
    assert qz.check(q, "") == ["3번 문장을 판단하지 않았어요"]


def test_generate_retries_when_check_fails(monkeypatch):
    calls = _fake(monkeypatch, CHOICE, CHOICE)
    verdicts = iter([["1번 틀림"], []])
    monkeypatch.setattr(qz, "check", lambda q, desc, card_id=None: next(verdicts))
    q = qz.generate("용어 뜻", "주당순이익", "")
    assert q.content["options"][q.key] == "주당순이익" and len(calls) == 2
    _fake(monkeypatch, *[CHOICE] * 3)
    monkeypatch.setattr(qz, "check", lambda q, desc, card_id=None: ["늘 틀림"])
    with pytest.raises(qz.QuizError, match="내용 검사 탈락"):
        qz.generate("용어 뜻", "주당순이익", "")


def test_ox_and_pairs_are_not_checked(monkeypatch):
    _fake(monkeypatch, {"statement": "s", "answer": True, "explanation": "e"})
    monkeypatch.setattr(qz, "check", lambda *a, **k: pytest.fail("O/X 는 검사하지 않는다"))
    assert qz.generate("O/X", "자사주 소각", "").kind == "O/X"


def test_chip_blank_uses_sonnet_others_haiku(monkeypatch):
    from generate.llm_client import HAIKU, SONNET
    chip = {"sentence": "회사가 ___ 를 사서 ___ 하면", "chips": ["자사주", "소각", "배당", "증자"],
            "answers": ["자사주", "소각"], "explanation": "e"}
    calls = _fake(monkeypatch, chip, CHOICE)
    qz.generate("칩 빈칸", "자사주 소각", "")
    qz.generate("용어 뜻", "주당순이익", "")
    assert [c["model"] for c in calls] == [SONNET, HAIKU] and qz.CHECK_MODEL == HAIKU


def test_wrong_explanation_fails_check(monkeypatch):
    # 보기는 맞는데 해설이 틀린 퀴즈: 마지막 문장(해설)이 거짓이면 탈락 (#237 리뷰)
    q = qz.to_quiz("용어 뜻", "주당순이익", CHOICE | {"explanation": "순이익 100원, 주식 10주면 주당순이익은 1원"})
    _judge(monkeypatch, ["참", "거짓", "거짓", "거짓"])
    problems = qz.check(q, "")
    assert len(problems) == 1 and "해설" in problems[0]
