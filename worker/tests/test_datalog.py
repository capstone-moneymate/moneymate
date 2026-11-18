import pytest

from concepts import datalog
from concepts.datalog import DatalogError, evaluate, parse
from concepts.graph import (DOWN, NORMAL, RULES, UP, ambiguous_pairs, build_graph, derive, effect, load_graph,
                            regime_out, regimes, signed_paths)

RULES_TEXT = RULES.read_text(encoding="utf-8")
BASE_RULES = "\n".join(str(r) for r in parse(RULES_TEXT).rules[:3])  # 평상시 규칙 3줄 (1~4단계 예시용)


def run(edges, rules=RULES_TEXT, **facts):
    return evaluate(parse(rules), {"edge": set(edges), **{k: set(v) for k, v in facts.items()}})


def effects(result):
    return result.get("effect")


def test_rules_file():
    # 교수님께 보여줄 규칙 파일: 평상시 영향 2줄 + 모호 1줄, 국면별 조건부 연결 6줄 (#158), 정답 경로 8줄 (#170)
    prog = parse(RULES_TEXT)
    assert [str(r) for r in prog.rules] == [
        "effect(X, Y, S) :- edge(X, Y, S).",
        "effect(X, Z, S1 * S2) :- effect(X, Y, S1), edge(Y, Z, S2).",
        "ambiguous(X, Y) :- effect(X, Y, 1), effect(X, Y, -1).",
        "overridden(X, Y, R) :- cond_edge(X, Y, _, R).",
        "edge_r(X, Y, S, R) :- edge(X, Y, S), regime(R), !overridden(X, Y, R).",
        "edge_r(X, Y, S, R) :- cond_edge(X, Y, S, R).",
        "effect_r(X, Y, S, R) :- edge_r(X, Y, S, R).",
        "effect_r(X, Z, S1 * S2, R) :- effect_r(X, Y, S1, R), edge_r(Y, Z, S2, R).",
        "ambiguous_r(X, Y, R) :- effect_r(X, Y, 1, R), effect_r(X, Y, -1, R).",
        "reach0(Y, Y) :- concept(Y).",
        "reach0(X, Y) :- effect(X, Y, _).",
        "step(X, Z, X, B) :- effect(X, Z, _), edge(X, B, _), reach0(B, Z).",
        "step(X, Z, A, B) :- step(X, Z, _, A), edge(A, B, _), reach0(B, Z).",
        "reach0_r(Y, Y, R) :- concept(Y), regime(R).",
        "reach0_r(X, Y, R) :- effect_r(X, Y, _, R).",
        "step_r(X, Z, X, B, R) :- effect_r(X, Z, _, R), edge_r(X, B, _, R), reach0_r(B, Z, R).",
        "step_r(X, Z, A, B, R) :- step_r(X, Z, _, A, R), edge_r(A, B, _, R), reach0_r(B, Z, R).",
    ]
    # overridden 을 먼저 다 알아야 !overridden 을 판단할 수 있어 2개 층으로 나뉜다
    layers = datalog.stratify(prog.rules)
    assert len(layers) == 2 and [r.head.pred for r in layers[0]].count("overridden") == 1


def test_step1_one_edge_is_one_effect():
    # 1단계: 연결(사실)이 있으면 영향(결론)이 생긴다
    r = run({("buyback", "share_count", -1)})
    assert effects(r) == {("buyback", "share_count", -1)}


def test_step2_chain_multiplies_signs():
    # 2단계: 자사주 취득 → 유통 주식 수(-1) → 주당순이익(-1) 이면 자사주 취득 → 주당순이익 (-1) × (-1) = +1
    r = run({("buyback", "share_count", -1), ("share_count", "eps", -1)})
    assert ("buyback", "eps", 1) in effects(r)
    # 공급계약 → 수주잔고(+1) → 매출(+1) = +1
    r = run({("supply", "backlog", 1), ("backlog", "revenue", 1)})
    assert ("supply", "revenue", 1) in effects(r)


def test_step3_fixpoint_rounds():
    # 3단계: 세 칸짜리 길. 1회차 한 칸, 2회차 두 칸, 3회차 세 칸, 4회차 새 사실 없음 → 고정점
    r = run({("ai", "gpu", 1), ("gpu", "hbm", 1), ("hbm", "memory", 1)}, rules=BASE_RULES)
    assert ("ai", "memory", 1) in effects(r)
    assert len(effects(r)) == 6        # 한 칸 3 + 두 칸 2 + 세 칸 1
    assert r.rounds == 4


def test_step4_ambiguous():
    # 4단계: X → Y → Z (+1), X → W → Z (-1) 이면 X, Z 는 모호
    r = run({("x", "y", 1), ("y", "z", 1), ("x", "w", 1), ("w", "z", -1)})
    assert r.get("ambiguous") == {("x", "z")}
    # 1주차 HBM 초안: 공급 → 메모리 가격(-1) → 실적(+1) 와 공급 → 실적(+1) 직접 연결이 함께 있으면 모호
    r = run({("hbm_supply", "memory_price", -1), ("memory_price", "semi_earnings", 1),
             ("hbm_supply", "semi_earnings", 1)})
    assert r.get("ambiguous") == {("hbm_supply", "semi_earnings")}


def test_cycle_still_stops():
    # 부호는 ±1 뿐이라 순환이 있어도 결론의 종류가 유한해 멈춘다
    r = run({("a", "b", 1), ("b", "a", -1)})
    assert ("a", "a", -1) in effects(r) and r.get("ambiguous") >= {("a", "b"), ("a", "a")}


def test_semi_naive_matches_naive_on_real_dictionary():
    # semi-naive(새 사실만 다시 보기) 결과가 "매 회차 전부 다시 보기"와 같은지 실제 사전으로 확인
    g = load_graph()
    edges = {(s, d, sign) for s, outs in g.out.items() for d, sign in outs}
    extra = {"cond_edge": set(g.cond), "regime": {(r,) for r in regimes(g)}, "concept": {(c,) for c in g.names}}
    fast = run(edges, **extra)
    prog = parse(RULES_TEXT)
    total = {"edge": set(edges), **extra}
    for layer in datalog.stratify(prog.rules):  # 단순(naive) 계산: 층마다 매 회차 전체로 모든 규칙을 다시 적용
        while True:
            found = {(rule.head.pred, datalog._ground(rule.head, b))
                     for rule in layer for b in datalog._join(rule.positive, -1, {}, total, negative=rule.negative)}
            added = {(p, f) for p, f in found if f not in total.get(p, set())}
            if not added:
                break
            for p, f in added:
                total.setdefault(p, set()).add(f)
    for pred in ("effect", "ambiguous", "edge_r", "effect_r", "ambiguous_r", "reach0", "step", "reach0_r", "step_r"):
        assert fast.get(pred) == total.get(pred, set()), pred


def search_paths(g, start, end, regime=NORMAL):
    """#170 전의 경로 탐색 (같은 개념을 두 번 지나지 않는 모든 경로). 규칙으로 바꾼 signed_paths 와 비교하는 기준."""
    out = regime_out(g, regime)
    found = []

    def walk(node, path, sign):
        if node == end and len(path) > 1:
            found.append((list(path), sign))
            return
        for nxt, s in out[node]:
            if nxt not in path:
                walk(nxt, path + [nxt], sign * s)

    walk(start, [start], 1)
    return sorted(found, key=lambda p: (len(p[0]), p[0]))


def test_engine_agrees_with_path_search_for_every_pair():
    # 실제 사전 29개의 모든 (시작, 결과) 쌍에서 엔진의 부호와 예전 경로 탐색의 부호가 같다 (#156 리팩터링 확인)
    g = load_graph()
    d = derive(g)
    for start in g.out:
        for end in g.out:
            if start == end:
                continue
            path_signs = {s for _, s in search_paths(g, start, end)}
            assert set(d.effects.get((start, end), ())) == path_signs, (start, end)
            effect(g, start, end, UP)  # 어긋나면 RuntimeError


# ------------------------------------------------------------------
# 정답 경로도 규칙으로 (#170): step(X, Z, A, B) = 연결 A → B 가 X → Z 경로 위에 있다
# ------------------------------------------------------------------

def test_step_keeps_only_edges_that_lead_to_the_end():
    # 손계산: a → b → c 와 a → d (d 에서는 c 로 못 감). a → c 경로 위의 연결은 a → b, b → c 둘뿐
    g = build_graph({k: k for k in "abcd"}, [("a", "b", "up"), ("b", "c", "down"), ("a", "d", "up")])
    assert derive(g).steps[("a", "c")] == {("a", "b"), ("b", "c")}
    assert signed_paths(g, "a", "c") == [(["a", "b", "c"], -1)]
    assert ("a", "d") not in derive(g).steps.get(("a", "c"), set())


def test_step_branches_give_every_path():
    # 손계산: x → y → z (+1)(+1) 와 x → w → z (+1)(-1). 연결 4개가 모두 경로 위에 있고 경로 2개, 모호
    g = build_graph({k: k for k in "xywz"}, [("x", "y", "up"), ("y", "z", "up"), ("x", "w", "up"), ("w", "z", "down")])
    assert derive(g).steps[("x", "z")] == {("x", "y"), ("y", "z"), ("x", "w"), ("w", "z")}
    assert signed_paths(g, "x", "z") == [(["x", "w", "z"], -1), (["x", "y", "z"], 1)]
    assert effect(g, "x", "z").direction == "ambiguous"


def test_no_path_means_no_steps():
    g = build_graph({k: k for k in "ab"}, [("a", "b", "up")])
    assert signed_paths(g, "b", "a") == [] and ("b", "a") not in derive(g).steps


def test_rule_paths_match_old_search_for_every_pair_and_regime():
    # 실제 사전 모든 국면 × 모든 (시작, 결과) 쌍에서 규칙으로 만든 경로 = 예전 탐색 경로 (순서·부호까지)
    g = load_graph()
    n_multi = 0
    for r in regimes(g):
        for start in g.out:
            for end in g.out:
                if start != end:
                    got = signed_paths(g, start, end, r)
                    assert got == search_paths(g, start, end, r), (r, start, end)
                    n_multi += len(got) > 1
    # 경로가 2개인 쌍: 인플레이션 → 국채 금리·은행 마진·성장주, AI 투자·GPU 수요 → 반도체 실적 (국면마다 5쌍)
    assert n_multi == 5 * len(regimes(g))


def test_real_dictionary_answer_order_from_rules():
    # 탭 1 정답 순서 예: 인하 → 국채 금리 → 성장주 가치평가. step 결론 2개를 이어 붙인 것
    g = load_graph()
    assert derive(g).steps[("rate_cut", "growth_valuation")] == {("rate_cut", "bond_yield"),
                                                                 ("bond_yield", "growth_valuation")}
    assert effect(g, "rate_cut", "growth_valuation").paths == [(["rate_cut", "bond_yield", "growth_valuation"], 1)]


def test_effect_raises_when_engine_and_paths_disagree():
    # 순환이 있는 사전은 엔진(순환을 도는 영향까지 셈)과 경로 탐색(같은 개념을 두 번 안 지남)이 어긋날 수 있다
    from concepts.graph import build_graph
    g = build_graph({"a": "a", "b": "b"}, [("a", "b", "up"), ("b", "a", "down")])
    with pytest.raises(RuntimeError, match="순환"):
        effect(g, "a", "b")


def test_facts_strings_comments_and_anonymous_vars():
    prog = parse('''
        % 주석
        edge("국채 금리", growth, -1).   // 따옴표 문자열과 소문자 상수
        has_out(X) :- edge(X, _, _).
    ''')
    r = evaluate(prog)
    assert r.get("has_out") == {("국채 금리",)}


def test_escaped_quote_does_not_end_string_or_start_comment():
    # 리뷰 반영: 문자열 안의 \" 뒤에 오는 % 를 주석으로 자르지 않는다
    r = evaluate(parse('p("a\\"%b"). % 진짜 주석'))
    assert r.get("p") == {('a"%b',)}


def test_anonymous_variable_does_not_collide_with_named_ones():
    # 리뷰 반영: _ 는 매번 다른 변수라 이름이 _1 인 변수와 섞이지 않는다
    r = evaluate(parse('q(a, b, c). p(X) :- q(_, _1, X).'))
    assert r.get("p") == {("c",)}


def test_underscore_prefixed_named_variable_allowed_in_head():
    # 리뷰 반영: _X 는 이름 있는 변수라 머리에 쓸 수 있다 (_ 하나만 막는다)
    r = evaluate(parse('q(a). p(_X) :- q(_X).'))
    assert r.get("p") == {("a",)}


# ------------------------------------------------------------------
# 부정과 국면별 조건부 연결 (#158)
# ------------------------------------------------------------------

def test_negation_means_no_such_fact():
    r = evaluate(parse('p(a). p(b). q(b). only_p(X) :- p(X), !q(X).'))
    assert r.get("only_p") == {("a",)}
    # q 는 규칙 없이 사실뿐이라 따로 계산할 층이 없다. 규칙 층은 하나
    assert r.strata == 1
    # q 를 규칙으로 만들면 only_p 는 q 보다 위층에 놓여 2개 층
    r = evaluate(parse('p(a). p(b). s(b). q(X) :- s(X). only_p(X) :- p(X), !q(X).'))
    assert r.get("only_p") == {("a",)} and r.strata == 2


def test_negation_order_in_body_does_not_matter():
    # 긍정 원자를 모두 맞춘 뒤 부정을 보므로 ! 가 앞에 와도 같은 결과 (#159 리뷰)
    facts = 'p(a). p(b). q(b). '
    front = evaluate(parse(facts + 'only_p(X) :- !q(X), p(X).'))
    back = evaluate(parse(facts + 'only_p(X) :- p(X), !q(X).'))
    assert front.get("only_p") == back.get("only_p") == {("a",)}


def test_negation_with_anonymous_means_none_at_all():
    # !has(X, _) 는 "X 로 시작하는 has 가 하나도 없음"
    r = evaluate(parse('n(a). n(b). has(a, 1). lonely(X) :- n(X), !has(X, _).'))
    assert r.get("lonely") == {("b",)}


def test_negation_printed_with_bang():
    assert str(parse("p(X) :- q(X), !r(X).").rules[0]) == "p(X) :- q(X), !r(X)."


def test_step5_regime_example():
    # 5단계: A → B (+1), B → C (+1), 경기 침체에서는 B → C 가 -1 → 평상시 A → C +1, 경기 침체 -1
    r = run({("a", "b", 1), ("b", "c", 1)}, cond_edge={("b", "c", -1, "recession")},
            regime={("normal",), ("recession",)})
    assert ("a", "c", 1, "normal") in r.get("effect_r")
    assert ("a", "c", -1, "recession") in r.get("effect_r")
    assert ("a", "c", 1, "recession") not in r.get("effect_r")   # 기본 연결은 그 국면에서 대체됐다
    assert ("a", "c", 1) in r.get("effect")                       # 평상시 규칙(1~3)은 그대로


def test_regime_only_edge_and_ambiguity():
    # 경기 침체에만 있는 연결(x → z)이 기존 경로(x → y → z, +1)와 부호가 다르면 그 국면에서만 모호
    r = run({("x", "y", 1), ("y", "z", 1)}, cond_edge={("x", "z", -1, "recession")},
            regime={("normal",), ("recession",)})
    assert r.get("ambiguous_r") == {("x", "z", "recession")}
    assert r.get("ambiguous") == set()


def test_real_dictionary_rate_cut_by_regime():
    # 실제 사전: 기준금리 인하 → 국채 금리(-1) → 성장주 가치평가. 평상시 -1 × -1 = +1, 경기 침체 -1 × +1 = -1
    g = load_graph()
    assert regimes(g) == [NORMAL, "recession"]
    assert effect(g, "rate_cut", "growth_valuation").direction == UP
    rec = effect(g, "rate_cut", "growth_valuation", regime="recession")
    assert rec.direction == DOWN and rec.paths == [(["rate_cut", "bond_yield", "growth_valuation"], -1)]
    # 조건부 연결이 없는 쌍은 국면을 바꿔도 같다
    assert effect(g, "buyback", "eps", regime="recession").direction == UP
    assert ambiguous_pairs(g, "recession") == []


def test_normal_regime_rules_match_plain_rules_for_every_pair():
    # 국면 규칙의 normal 결론(effect_r ... normal)이 평상시 규칙(effect)과 모든 쌍에서 같다
    d = derive(load_graph())
    normal_r = {(x, y): s for (x, y, r), s in d.effects_r.items() if r == NORMAL}
    assert normal_r == d.effects


def test_every_pair_every_regime_engine_matches_paths():
    # 모든 국면·모든 쌍에서 엔진 결론 = 그 국면 연결로 찾은 경로 (어긋나면 effect 가 RuntimeError)
    g = load_graph()
    for r in regimes(g):
        for start in g.out:
            for end in g.out:
                if start != end:
                    effect(g, start, end, regime=r)


@pytest.mark.parametrize("cond, message", [
    ([("a", "missing", "up", "recession")], "없는 개념"),
    ([("a", "b", "UP", "recession")], "force_dir"),
    ([("a", "b", "up", "Recession")], "국면 이름"),
    ([("a", "b", "up", "normal")], "국면 이름"),
    ([("a", "b", "up", "recession"), ("a", "b", "down", "recession")], "방향이 둘"),
])
def test_build_graph_rejects_bad_cond_edges(cond, message):
    with pytest.raises(ValueError, match=message):
        build_graph({"a": "a", "b": "b"}, [("a", "b", "down")], cond)


def test_unknown_regime():
    with pytest.raises(ValueError, match="모르는 국면"):
        effect(load_graph(), "rate_cut", "growth_valuation", regime="boom")


@pytest.mark.parametrize("text, message", [
    ("p(X) :- q(X), !p(X).", "순환"),                 # "p 가 없으면 p": 층을 나눌 수 없음
    ("p(X) :- !q(X).", "! 없는 원자"),                # 긍정 원자가 하나도 없음
    ("p(X) :- q(X), !r(Y).", "몸통의 긍정 원자에 없어요"),  # 부정 원자의 이름 있는 변수가 안 묶임
])
def test_negation_errors(text, message):
    with pytest.raises(DatalogError, match=message):
        parse(text)


@pytest.mark.parametrize("text, message", [
    ("p(X) :- q(Y).", "몸통에 없어요"),             # 안전하지 않은 규칙
    ("p(X) :- q(X * 2).", "머리에서만"),            # 곱은 머리에서만
    ("p(X).", "사실에는 변수"),                     # 변수가 있는 사실
    ("p(X) :- q(X)", "'.'"),                        # 마침표 빠짐
    ("P(x).", "소문자"),                            # 관계 이름은 소문자
    ("p(_) :- q(_).", "머리의 변수"),               # 머리의 _ 는 몸통 _ 와 다른 변수
    ("p(x) # q.", "읽을 수 없는"),
])
def test_parse_errors(text, message):
    with pytest.raises(DatalogError, match=message):
        parse(text)


def test_product_needs_integers():
    with pytest.raises(DatalogError, match="정수"):
        evaluate(parse("p(X * Y) :- q(X, Y)."), {"q": {("a", 1)}})
