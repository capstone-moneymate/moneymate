import pytest

from concepts.graph import (AMBIGUOUS, DOWN, UP, ambiguous_pairs, build_graph, effect, find_any_cycle, find_cycle, load_graph,
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
    assert len(g.names) == 29
    assert find_cycle(g) is None
    assert find_any_cycle(g) is None   # 국면별 조건부 연결까지 넣어도 순환 없음
    # 인하 → 국채 금리 ▼ → 성장주 ▲ : (-1) × (-1) = +1
    assert effect(g, "rate_cut", "growth_valuation").direction == UP
    # 인상 → 국채 금리 ▲ → 성장주 ▼ : (+1) × (-1) = -1. 직접 연결은 지워서 경로는 하나다
    e = effect(g, "rate_hike", "growth_valuation")
    assert e.direction == DOWN and len(e.paths) == 1
    # 금리와 AI 테마를 잇던 연결은 근거가 없어 지웠다
    assert effect(g, "rate_cut", "ai_investment").direction is None
    # HBM 공급 확대 → 범용 메모리 가격 ▲ → 반도체 기업 실적 ▲
    assert effect(g, "hbm_supply", "semi_earnings").direction == UP
    # 자사주 취득 → 유통 주식 수 ▼ → 주당순이익 ▲ : (-1) × (-1) = +1
    assert effect(g, "buyback", "eps").direction == UP
    # 보유 자기주식 소각은 발행주식 총수만 줄인다. 유통 주식 수는 취득 때 이미 줄어서 주당순이익과 이어지지 않는다
    assert effect(g, "share_cancel", "eps").direction is None
    # 자사주 취득 → 소각 ▲ (1년 내 소각 의무) → 발행주식 총수 ▼ : (+1) × (-1) = -1
    assert effect(g, "buyback", "issued_shares").direction == DOWN
    # 기업 순이익 → 주당순이익 ▲ (분자) : +1
    assert effect(g, "corp_earnings", "eps").direction == UP
    # 공급계약 체결 → 수주잔고 ▲ → 매출 ▲ : (+1) × (+1) = +1
    assert effect(g, "supply_contract_win", "revenue").direction == UP
    # 매출이 늘어도 비용에 따라 순이익은 달라져 연결하지 않았다
    assert effect(g, "revenue", "corp_earnings").direction is None
    # 신규 시설투자 → 생산능력 ▲ : +1
    assert effect(g, "capex", "capacity").direction == UP
    # AI 반도체 수요 → HBM 수요 ▲ → 반도체 설비투자 ▲ → 생산능력 ▲ : +1. 직접 연결은 넣지 않아 경로는 하나다
    e = effect(g, "gpu_demand", "capacity")
    assert e.direction == UP and len(e.paths) == 1
    # 반도체 설비투자는 일반 시설투자와 나눴다: 다른 업종 시설투자에 AI 반도체 수요 경로가 붙지 않는다
    assert effect(g, "gpu_demand", "capex").direction is None


@pytest.mark.parametrize("force", ["down", "up"])
def test_cycle_only_in_a_regime(force):
    # 평상시 a → b 뿐이라 순환이 없지만, 침체 때만 b → a 가 생기면 그 국면에 순환이 있다 (#159 리뷰).
    # ▼ 순환이면 모호 쌍 계산이 RuntimeError 로 죽고, ▲ 순환이면 모호 쌍 없이 그냥 지나가던 것을 미리 막는다
    g = build_graph({"a": "a", "b": "b"}, [("a", "b", "up")], [("b", "a", force, "recession")])
    assert find_cycle(g) is None
    assert find_cycle(g, "recession") == ["a", "b", "a"]
    assert find_any_cycle(g) == ("recession", ["a", "b", "a"])


def test_cli_reports_regime_cycle_instead_of_crashing(monkeypatch, capsys):
    import concepts.graph as graph
    g = build_graph({"a": "a", "b": "b"}, [("a", "b", "up")], [("b", "a", "down", "recession")])
    monkeypatch.setattr(graph, "load_graph", lambda: g)
    assert graph.main([]) == 1
    assert "순환: 있음 [recession]" in capsys.readouterr().out


def test_cli_pair_query_checks_cycle_in_requested_regime(monkeypatch, capsys):
    # 침체 때만 b → a 순환: 침체로 물으면 RuntimeError 대신 순환을 알리고 1, 평상시로 물으면 그대로 답한다 (#159 리뷰)
    import concepts.graph as graph
    g = build_graph({"a": "a", "b": "b"}, [("a", "b", "up")], [("b", "a", "down", "recession")])
    monkeypatch.setattr(graph, "load_graph", lambda: g)
    assert graph.main(["--from", "a", "--to", "b", "--regime", "recession"]) == 1
    assert "[recession] 순환이 있어" in capsys.readouterr().out
    assert graph.main(["--from", "a", "--to", "b"]) == 0
    assert "상승 압력" in capsys.readouterr().out
