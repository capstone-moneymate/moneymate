"""개념 지도 선수 관계 순환 검사와 ready (#199). 손으로 만든 작은 그래프로, 손계산과 같은지 본다."""
from concepts.prereq_check import Checked, break_cycles, cycle_edges, ready_concepts

# 순환 없음: 순이익 → EPS, 주식 수 → EPS, EPS → PER
#   순이익 ─┐
#           ├→ EPS → PER
#   주식 수 ─┘
EDGES = [("순이익", "EPS", 4), ("주식 수", "EPS", 3), ("EPS", "PER", 4)]
CONCEPTS = ["순이익", "주식 수", "EPS", "PER"]


def test_no_cycle():
    assert cycle_edges(EDGES) == set()
    assert break_cycles(EDGES) == Checked(EDGES, [])


def test_one_cycle_drops_fewest_votes_then_name():
    # a → b(3) → c(4) → a(3) 는 순환, c → d(4) 는 순환 밖
    edges = [("a", "b", 3), ("b", "c", 4), ("c", "a", 3), ("c", "d", 4)]
    assert cycle_edges(edges) == {("a", "b"), ("b", "c"), ("c", "a")}   # c → d 는 순환 위가 아니다
    # 표가 가장 적은 것: (a,b,3) 와 (c,a,3) 동점 → 이름 순으로 (a,b) 를 뺀다
    assert break_cycles(edges) == Checked([("b", "c", 4), ("c", "a", 3), ("c", "d", 4)], [("a", "b", 3)])


def test_two_cycles_removed_one_at_a_time():
    edges = [("a", "b", 4), ("b", "a", 3), ("c", "d", 3), ("d", "c", 4)]
    out = break_cycles(edges)
    assert out.removed == [("b", "a", 3), ("c", "d", 3)]                 # 표 3 끼리 이름 순: (b,a) 먼저
    assert out.kept == [("a", "b", 4), ("d", "c", 4)]
    assert cycle_edges(out.kept) == set()


def test_self_loop_is_a_cycle():
    assert break_cycles([("a", "a", 4), ("a", "b", 4)]) == Checked([("a", "b", 4)], [("a", "a", 4)])


def test_ready_by_hand():
    # 순이익만 앎 → 주식 수(선수 없음, 모름)만 준비됨. EPS 는 주식 수를 몰라서, PER 은 EPS 를 몰라서 아직
    assert ready_concepts("u1", CONCEPTS, EDGES, {"순이익": 0.97, "주식 수": 0.5}) == ["주식 수"]
    # 순이익·주식 수를 앎 → EPS 준비됨. 이미 아는 개념은 빠진다
    assert ready_concepts("u1", CONCEPTS, EDGES, {"순이익": 0.97, "주식 수": 0.96}) == ["EPS"]
    # 아무것도 모름 → 선수 개념이 없는 둘
    assert ready_concepts("u1", CONCEPTS, EDGES, {}) == ["순이익", "주식 수"]
    # 다 앎 → 없음
    assert ready_concepts("u1", CONCEPTS, EDGES, {c: 0.99 for c in CONCEPTS}) == []


def test_ready_threshold_is_inclusive():
    m = {"순이익": 0.95, "주식 수": 0.9499}
    assert ready_concepts("u1", CONCEPTS, EDGES, m) == ["주식 수"]          # 0.95 는 앎, 0.9499 는 모름
    assert ready_concepts("u1", CONCEPTS, EDGES, m, know_p=0.9) == ["EPS"]


def test_ready_two_users_differ():
    # 완료 기준(1-3)과 같은 모양: 지식 상태가 다르면 준비된 개념도 다르다
    a = ready_concepts("a", CONCEPTS, EDGES, {"순이익": 0.99, "주식 수": 0.99})
    b = ready_concepts("b", CONCEPTS, EDGES, {"주식 수": 0.99})
    assert a == ["EPS"] and b == ["순이익"]
