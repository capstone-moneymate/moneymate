"""개념 지도 ③ 같은 뜻 묶기. 실제 모델 없이 손으로 만든 유사도·벡터로 본다."""
import numpy as np

from concepts.concept_map import Term
from concepts.term_groups import group_indices, group_terms, make_nodes, pair_scores

# 0 금리 인상, 1 기준금리 인상, 2 금리 인하, 3 EPS, 4 주당순이익
SIM = np.array([
    [1.00, 0.90, 0.85, 0.10, 0.10],
    [0.90, 1.00, 0.70, 0.10, 0.10],
    [0.85, 0.70, 1.00, 0.10, 0.10],
    [0.10, 0.10, 0.10, 1.00, 0.80],
    [0.10, 0.10, 0.10, 0.80, 1.00],
])


def test_complete_linkage_does_not_chain():
    # 금리 인하는 금리 인상과 0.85 로 비슷하지만 기준금리 인상과는 0.70 이라, 기준 0.8 에서 합치지 않는다.
    # 단일 연결이었다면 0-1(0.90), 0-2(0.85) 로 셋이 사슬처럼 합쳐진다
    assert group_indices(SIM, 0.8) == [[0, 1], [2], [3, 4]]


def test_threshold_moves_groups():
    assert group_indices(SIM, 0.95) == [[0], [1], [2], [3], [4]]
    assert group_indices(SIM, 0.65) == [[0, 1, 2], [3, 4]]
    assert group_indices(SIM, 0.05) == [[0, 1, 2, 3, 4]]


def test_group_indices_edge_sizes():
    assert group_indices(np.ones((1, 1)), 0.5) == [[0]]
    assert group_indices(np.zeros((0, 0)), 0.5) == []


def test_pair_scores_hand_count():
    gold = ["hike", "hike", "cut", "eps", "eps"]           # 정답 쌍: (0,1), (3,4)
    s = pair_scores([[0, 1, 2], [3, 4]], gold)              # 묶은 쌍: (0,1) (0,2) (1,2) (3,4)
    assert s["pred_pairs"] == 4 and s["true_pairs"] == 2
    assert s["precision"] == 2 / 4 and s["recall"] == 2 / 2
    assert abs(s["f1"] - 2 * 0.5 * 1 / 1.5) < 1e-9
    assert pair_scores([[0], [1], [2], [3], [4]], gold) == {
        "precision": 1.0, "recall": 0.0, "f1": 0.0, "pred_pairs": 0, "true_pairs": 2}


def test_make_nodes_label_is_most_used_term():
    terms = [Term("EPS", "약어", [1]), Term("주당순이익", "순이익 ÷ 주식 수", [2, 3]), Term("환율", "", [1])]
    nodes = make_nodes(terms, [[0, 1], [2]])
    assert nodes[0].label == "주당순이익" and nodes[0].aliases == ["EPS"]
    assert nodes[0].desc == "순이익 ÷ 주식 수" and nodes[0].card_ids == [1, 2, 3]
    assert nodes[1].label == "환율" and nodes[1].aliases == []


def test_make_nodes_tie_keeps_first():
    nodes = make_nodes([Term("EPS", "", [1]), Term("주당순이익", "", [2])], [[0, 1]])
    assert nodes[0].label == "EPS"


def test_group_terms_with_fake_encoder():
    vecs = {"EPS": [1, 0], "주당순이익": [0.96, 0.28], "환율": [0, 1]}   # 길이 1 벡터, EPS·주당순이익 유사도 0.96

    def encode(texts):
        return np.array([vecs[t] for t in texts], dtype=float)

    terms = [Term(t, "", [i]) for i, t in enumerate(vecs)]
    nodes = group_terms(terms, encode, threshold=0.9)
    assert [(n.label, n.aliases) for n in nodes] == [("EPS", ["주당순이익"]), ("환율", [])]
    assert group_terms([], encode, 0.9) == []
