import pytest

from concepts import datalog
from concepts.datalog import DatalogError, evaluate, parse
from concepts.graph import RULES, UP, derive, effect, load_graph, signed_paths

RULES_TEXT = RULES.read_text(encoding="utf-8")


def run(edges, rules=RULES_TEXT):
    return evaluate(parse(rules), {"edge": set(edges)})


def effects(result):
    return result.get("effect")


def test_rules_file_has_three_rules():
    # 교수님께 보여줄 규칙 파일: 영향 2줄 + 모호 1줄
    prog = parse(RULES_TEXT)
    assert [str(r) for r in prog.rules] == [
        "effect(X, Y, S) :- edge(X, Y, S).",
        "effect(X, Z, S1 * S2) :- effect(X, Y, S1), edge(Y, Z, S2).",
        "ambiguous(X, Y) :- effect(X, Y, 1), effect(X, Y, -1).",
    ]


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
    r = run({("ai", "gpu", 1), ("gpu", "hbm", 1), ("hbm", "memory", 1)})
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
    edges = {(s, d, sign) for s, outs in load_graph().out.items() for d, sign in outs}
    fast = run(edges)
    prog = parse(RULES_TEXT)
    total = {"edge": set(edges)}
    while True:  # 단순(naive) 계산: 매 회차 전체로 모든 규칙을 다시 적용
        found = {(rule.head.pred, datalog._ground(rule.head, b))
                 for rule in prog.rules for b in datalog._join(rule.body, -1, {}, total)}
        added = {(p, f) for p, f in found if f not in total.get(p, set())}
        if not added:
            break
        for p, f in added:
            total.setdefault(p, set()).add(f)
    assert fast.get("effect") == total["effect"] and fast.get("ambiguous") == total.get("ambiguous", set())


def test_engine_agrees_with_path_search_for_every_pair():
    # 실제 사전 29개의 모든 (시작, 결과) 쌍에서 엔진의 부호와 예전 경로 탐색의 부호가 같다 (#156 리팩터링 확인)
    g = load_graph()
    d = derive(g)
    for start in g.out:
        for end in g.out:
            if start == end:
                continue
            path_signs = {s for _, s in signed_paths(g, start, end)}
            assert set(d.effects.get((start, end), ())) == path_signs, (start, end)
            effect(g, start, end, UP)  # 어긋나면 RuntimeError


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
