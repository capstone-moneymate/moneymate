"""튜터 퀴즈 7종류: 찍어서 맞힐 확률 손계산, 모양 검사, 채점, 출제 재시도. 실제 API 는 부르지 않는다."""
import json
from types import SimpleNamespace

import pytest

from tutor import quiz as qz

CHOICE = {"question": "EPS 의 뜻은?", "options": ["주당순이익", "주가수익비율", "자기자본"], "answer_index": 0,
          "explanation": "순이익을 주식 수로 나눈 값"}


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
    assert q.content == {"question": "EPS 의 뜻은?", "options": ["주당순이익", "주가수익비율", "자기자본"]}
    assert q.key == 0 and "answer_index" not in q.content
    assert qz.grade(q, 0) and not qz.grade(q, 1)


@pytest.mark.parametrize("change, msg", [
    ({"options": ["a", "b"]}, "보기가 3개"),
    ({"options": ["a", "a", "b"]}, "같은 보기"),
    ({"answer_index": 3}, "범위 밖"),
    ({"explanation": "지금 매수 추천"}, "금지 표현"),
])
def test_choice_quiz_errors(change, msg):
    with pytest.raises(qz.QuizError, match=msg):
        qz.to_quiz("용어 뜻", "주당순이익", CHOICE | change)


def test_confusable_pair_must_use_both_names():
    data = CHOICE | {"options": ["주당순이익", "주당순자산"], "answer_index": 1}
    assert qz.to_quiz("헷갈리는 쌍", "주당순이익", data, pair=["주당순이익", "주당순자산"]).key == 1
    with pytest.raises(qz.QuizError, match="두 개념 이름"):
        qz.to_quiz("헷갈리는 쌍", "주당순이익", data | {"options": ["EPS", "BPS"]}, pair=["주당순이익", "주당순자산"])


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
    return calls


def test_generate_retries_bad_shape_then_ok(monkeypatch):
    calls = _fake(monkeypatch, CHOICE | {"options": ["a"]}, CHOICE)
    q = qz.generate("용어 뜻", "주당순이익", "순이익 ÷ 주식 수")
    assert q.content["options"][q.key] == "주당순이익" and len(calls) == 2 and calls[0]["module"] == "tutor_quiz"
    assert '"desc": "순이익 ÷ 주식 수"' in calls[0]["messages"][0]["content"]


def test_generate_gives_up(monkeypatch):
    _fake(monkeypatch, CHOICE | {"options": ["a"]}, CHOICE | {"options": ["a"]})
    with pytest.raises(qz.QuizError, match="보기가 3개"):
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
        assert q.content["options"][q.key] == "주당순이익" and sorted(q.content["options"]) == sorted(CHOICE["options"])
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
