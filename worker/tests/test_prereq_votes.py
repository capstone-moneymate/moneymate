"""개념 지도 ④ 선수 관계 다수결. 실제 API 는 부르지 않는다 (ask_once 나 create 를 가짜로 바꾼다)."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from concepts import prereq_votes as pv
from concepts.prereq_votes import Prereq, candidate_pairs, decide
from concepts.term_groups import ConceptNode

NODES = [
    ConceptNode("순이익", "회사가 번 돈", [], [1]),        # 0
    ConceptNode("주당순이익", "순이익 ÷ 주식 수", [], [1, 2]),  # 1
    ConceptNode("주식 수", "", [], [2]),                 # 2
    ConceptNode("환율", "", [], [3]),                    # 3
]


def test_candidates_cooccur_first_then_neighbors():
    sim = np.array([
        [1.0, 0.9, 0.2, 0.6],
        [0.9, 1.0, 0.5, 0.1],
        [0.2, 0.5, 1.0, 0.3],
        [0.6, 0.1, 0.3, 1.0],
    ])
    # 같은 카드: (0,1) 카드1, (1,2) 카드2. 이웃 top1: 0→1, 1→0, 2→1, 3→0  → 새 쌍은 (0,3) 하나
    assert candidate_pairs(NODES, sim, top_k=1) == [(0, 1), (1, 2), (0, 3)]
    assert candidate_pairs(NODES, sim, top_k=1, max_pairs=2) == [(0, 1), (1, 2)]   # 같은 카드 쌍이 먼저 남는다
    assert candidate_pairs(NODES, None) == [(0, 1), (1, 2)]                       # 임베딩 없으면 같은 카드 쌍만


def test_decide_majority_by_hand():
    assert decide(0, 1, {"i_first": 2, "j_first": 0, "none": 1}) == Prereq(0, 1, 2, 3)
    assert decide(0, 1, {"i_first": 0, "j_first": 3, "none": 0}) == Prereq(1, 0, 3, 3)   # 뒤가 먼저면 방향을 뒤집어 저장
    assert decide(0, 1, {"i_first": 1, "j_first": 1, "none": 1}) is None                # 갈림
    assert decide(0, 1, {"i_first": 1, "j_first": 0, "none": 2}) is None                # 관계 없음이 과반


def test_vote_pair_swaps_order_and_maps_back(monkeypatch):
    shown = []

    def ask(x, y):
        shown.append((x.label, y.label))
        return "first" if x.label == "순이익" else "second"  # 늘 "순이익이 먼저"라고 답하는 일관된 가짜

    monkeypatch.setattr(pv, "ask_once", ask)
    count = pv.vote_pair(NODES, 0, 1)
    assert shown == [("순이익", "주당순이익"), ("주당순이익", "순이익")] * 2
    assert count == {"i_first": 4, "j_first": 0, "none": 0}   # 순서를 바꿔도 같은 방향으로 센다


def test_position_bias_does_not_make_an_edge(monkeypatch):
    monkeypatch.setattr(pv, "ask_once", lambda x, y: "first")   # 무조건 앞에 나온 쪽을 고르는 버릇
    count = pv.vote_pair(NODES, 0, 1)                           # 기본 4번: 원래 순서 2 + 바꾼 순서 2
    assert count == {"i_first": 2, "j_first": 2, "none": 0}     # 정확히 상쇄
    assert decide(0, 1, count) is None


def test_position_bias_with_three_votes_would_pass(monkeypatch):
    # 3번이었다면 버릇만으로 2:1 이 되어 연결이 생긴다. VOTES 를 4로 둔 이유
    monkeypatch.setattr(pv, "ask_once", lambda x, y: "first")
    count = pv.vote_pair(NODES, 0, 1, votes=3)
    assert count == {"i_first": 2, "j_first": 1, "none": 0}
    assert decide(0, 1, count) == Prereq(0, 1, 2, 3)


def test_decide_four_votes_needs_three():
    assert decide(0, 1, {"i_first": 3, "j_first": 1, "none": 0}) == Prereq(0, 1, 3, 4)
    assert decide(0, 1, {"i_first": 2, "j_first": 0, "none": 2}) is None


def test_build_prereqs_counts(monkeypatch):
    answers = {("순이익", "주당순이익"): "first", ("주당순이익", "순이익"): "second",
               ("주당순이익", "주식 수"): "none", ("주식 수", "주당순이익"): "none"}
    monkeypatch.setattr(pv, "ask_once", lambda x, y: answers[(x.label, y.label)])
    edges, stats = pv.build_prereqs(NODES, [(0, 1), (1, 2)])
    assert edges == [Prereq(0, 1, 4, 4)]
    assert stats == {"pairs": 2, "calls": 8, "edges": 1, "split": 0, "none": 1}


def test_ask_once_uses_schema_and_raises_on_cut(monkeypatch):
    calls = []

    def create(module, **kw):
        calls.append(kw)
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps({"reason": "r", "answer": "none"}))])

    monkeypatch.setattr(pv, "create", create)
    assert pv.ask_once(NODES[0], NODES[1]) == "none"
    assert calls[0]["output_config"]["format"]["schema"]["properties"]["answer"]["enum"] == ["first", "second", "none"]
    assert '"X": {"name": "순이익"' in calls[0]["messages"][0]["content"]

    monkeypatch.setattr(pv, "create", lambda module, **kw: SimpleNamespace(stop_reason="max_tokens", content=[]))
    with pytest.raises(RuntimeError):
        pv.ask_once(NODES[0], NODES[1])
