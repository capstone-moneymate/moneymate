import pytest

from concepts.graph import (AMBIGUOUS, DOWN, UP, ambiguous_pairs, build_graph, effect, find_cycle, load_graph,
                            signed_paths)

# 손계산용 작은 사전. 멘토 자료의 파월 예시 + 모호성 예시(X → Y·W → Z)
NAMES = {c: c for c in ["cut_expect", "rate_long", "pv", "growth", "x", "y", "w", "z"]}
EDGES = [
    ("cut_expect", "rate_long", "down"),   # 인하 기대가 커지면 금리 장기 유지를 누른다
    ("rate_long", "pv", "down"),           # 금리가 오래 유지되면 미래 현금의 현재가치를 누른다
    ("pv", "growth", "up"),                # 현재가치가 커지면 성장주를 올린다
    ("x", "y", "up"), ("y", "z", "up"),    # 위 경로: + × + = +
    ("x", "w", "up"), ("w", "z", "down"),  # 아래 경로: + × - = -
]


@pytest.fixture
def g():
    return build_graph(NAMES, EDGES)


def test_signed_paths_sign_is_product(g):
    # (-1) × (-1) × (+1) = +1
    assert signed_paths(g, "cut_expect", "growth") == [(["cut_expect", "rate_long", "pv", "growth"], 1)]


def test_effect_powell_example(g):
    # 파월 "인하를 서두르지 않겠다" = 인하 기대가 줄어듦(down) → +1 × -1 = -1 → 성장주 하락 압력
    assert effect(g, "cut_expect", "growth", change=DOWN).direction == DOWN
    assert effect(g, "cut_expect", "growth", change=UP).direction == UP
    # 중간 개념까지: 인하 기대 줄어듦 → 금리 장기 유지 ▲ (-1 × -1)
    assert effect(g, "cut_expect", "rate_long", change=DOWN).direction == UP


def test_effect_ambiguous_when_signs_differ(g):
    e = effect(g, "x", "z")
    assert e.direction == AMBIGUOUS
    assert sorted(s for _, s in e.paths) == [-1, 1]


def test_effect_no_path(g):
    assert effect(g, "growth", "cut_expect").direction is None   # 거꾸로는 경로 없음
    assert effect(g, "x", "growth").paths == []


def test_ambiguous_pairs_finds_only_x_z(g):
    assert [(e.start, e.end) for e in ambiguous_pairs(g)] == [("x", "z")]


def test_find_cycle():
    assert find_cycle(build_graph(NAMES, EDGES)) is None
    cyc = find_cycle(build_graph({"a": "a", "b": "b", "c": "c"},
                                 [("a", "b", "up"), ("b", "c", "up"), ("c", "a", "down")]))
    assert cyc == ["a", "b", "c", "a"]


def test_cycle_does_not_loop_forever_in_paths():
    g = build_graph({"a": "a", "b": "b"}, [("a", "b", "up"), ("b", "a", "up")])
    assert signed_paths(g, "a", "b") == [(["a", "b"], 1)]


def test_build_graph_rejects_bad_input():
    with pytest.raises(ValueError):
        build_graph({"a": "a"}, [("a", "missing", "up")])
    with pytest.raises(ValueError):
        build_graph({"a": "a", "b": "b"}, [("a", "b", "UP")])
    with pytest.raises(ValueError):
        signed_paths(build_graph({"a": "a"}, []), "a", "missing")


def test_seed_dictionary():
    # 실제 개념 사전 (db/seeds). 연결이 바뀌면 손계산도 다시 확인한다
    g = load_graph()
    assert len(g.names) == 17
    assert find_cycle(g) is None
    # 인하 → 국채 금리 ▼ → 성장주 ▲ : (-1) × (-1) = +1
    assert effect(g, "rate_cut", "growth_valuation").direction == UP
    # 인상 → 성장주: 직접 ▼, 국채 금리 경로 (+1) × (-1) = ▼ → 두 경로가 같은 방향
    e = effect(g, "rate_hike", "growth_valuation")
    assert e.direction == DOWN and len(e.paths) == 2
    # HBM 공급 확대 → 범용 메모리 가격 ▲ → 반도체 기업 실적 ▲
    assert effect(g, "hbm_supply", "semi_earnings").direction == UP
