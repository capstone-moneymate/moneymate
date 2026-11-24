"""개념 지도 ③ 같은 뜻 묶기. 실제 모델 없이 손으로 만든 유사도·벡터로 본다."""
import numpy as np

from concepts import term_groups as tg
from concepts.concept_map import Term
from concepts.term_groups import ConceptNode, confusable_pairs, group_indices, group_terms, make_nodes, pair_scores

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


def test_confusable_pairs_by_hand():
    # 기준 0.8 묶음: [금리 인상, 기준금리 인상] [금리 인하] [EPS, 주당순이익]
    # 묶음 사이 가장 가까운 쌍: 첫 묶음·금리 인하 = max(0.85, 0.70) = 0.85 → 헷갈리는 쌍. 나머지는 0.10
    names = ["금리 인상", "기준금리 인상", "금리 인하", "EPS", "주당순이익"]
    groups = group_indices(SIM, 0.8)
    nodes = make_nodes([Term(n, "", [1]) for n in names], groups)
    assert confusable_pairs(nodes, groups, SIM) == {"금리 인상": ["금리 인하"], "금리 인하": ["금리 인상"]}
    assert confusable_pairs(nodes, groups, SIM, low=0.9) == {}


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


def test_make_nodes_keeps_step2_variants_as_aliases():
    t = Term("자사주 취득", "", [1, 2])
    t.variants = ["자기주식 취득"]
    nodes = make_nodes([t, Term("자사주 매입", "", [3])], [[0, 1]])
    assert nodes[0].label == "자사주 취득" and nodes[0].aliases == ["자사주 매입", "자기주식 취득"]


def test_same_meaning_threshold():
    from concepts.term_groups import same_meaning

    def encode(texts):   # 길이 1 벡터: a·b = 0.8, a·c = 0.6
        v = {"a": [1.0, 0.0], "b": [0.8, 0.6], "c": [0.6, 0.8]}
        return np.array([v[t] for t in texts])

    assert same_meaning(encode, "a", "b") and not same_meaning(encode, "a", "c")


# --- 헷갈리는 이웃 후보와 사람 검토 (#228) ---

def _four():
    # 0 적자전환, 1 흑자전환, 2 적자, 3 매출액. 0-1 0.85, 0-2 0.80, 1-2 0.72, 2-3 0.71, 0-3 0.70, 1-3 0.50
    sim = np.array([[1, .85, .80, .70], [.85, 1, .72, .50], [.80, .72, 1, .71], [.70, .50, .71, 1]])
    nodes = [ConceptNode(x, "", [], []) for x in ["적자전환", "흑자전환", "적자", "매출액"]]
    return nodes, [[0], [1], [2], [3]], sim


def test_confusable_candidates_top_of_either_side():
    nodes, groups, sim = _four()
    # top=1: 0→1, 1→0, 2→0, 3→2 → 쌍 (0,1) (0,2) (2,3). 유사도 높은 순
    assert tg.confusable_candidates(nodes, groups, sim, top=1) == [(0, 1, 0.85), (0, 2, 0.8), (2, 3, 0.71)]
    assert tg.confusable_candidates(nodes, groups, sim, low=0.9) == []


def test_confusable_review_merge_keep_only_and_map():
    nodes, groups, sim = _four()
    rows = [tg.ConfusableRow("적자전환", "흑자전환", "0.850", "keep"), tg.ConfusableRow("매출액", "적자", "0.710", "drop")]
    added = tg.merge_confusable(rows, nodes, tg.confusable_candidates(nodes, groups, sim, top=1))
    assert added == 1 and rows[2] == tg.ConfusableRow("적자전환", "적자", "0.800")   # 이미 있는 쌍은 순서가 달라도 안 더함
    kept, missing = tg.reviewed_confusable(rows, nodes)
    assert kept == [(0, 1, 0.85)] and missing == []                              # 빈칸·drop 은 안 넣는다
    assert tg.confusable_map(nodes, kept) == {"적자전환": ["흑자전환"], "흑자전환": ["적자전환"]}


def test_confusable_review_drop_wins_and_missing_names():
    nodes = [ConceptNode("자기주식", "", ["자사주"], []), ConceptNode("자사주 취득", "", [], [])]
    rows = [tg.ConfusableRow("자기주식", "자사주 취득", "0.8", "keep"), tg.ConfusableRow("자사주", "자사주 취득", "", "drop"),
            tg.ConfusableRow("없는 이름", "자기주식", "", "keep")]
    kept, missing = tg.reviewed_confusable(rows, nodes)
    assert kept == [] and [(r.a, r.b) for r in missing] == [("없는 이름", "자기주식")]


def test_confusable_review_file_roundtrip(tmp_path):
    p = tmp_path / "c.csv"
    rows = [tg.ConfusableRow("적자", "적자전환", "0.800", "keep", "사람 검토")]
    tg.save_confusable_review(rows, p)
    assert tg.load_confusable_review(p) == rows and tg.load_confusable_review(tmp_path / "x.csv") == []
