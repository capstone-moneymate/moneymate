"""개념 지도 ③ 같은 뜻 묶기 (사람1, #198). 로컬 임베딩으로 "EPS" 와 "주당순이익" 을 한 개념 노드로 묶는다.

방법
- 용어마다 임베딩 벡터를 만들고 (정규화해서 내적 = 코사인 유사도), 유사도가 기준값 이상인 것끼리 묶는다
- 묶을 때는 "완전 연결(complete linkage)": 두 묶음을 합치려면 **모든 쌍**이 기준값 이상이어야 한다.
  한 쌍만 비슷해도 합치는 방식(단일 연결)은 "금리 인상 ~ 금리 ~ 금리 인하" 처럼 사슬로 이어져 반대말까지 합친다
- 기준값과 모델은 인과 사전 별칭(사람이 쓴 정답)으로 고른다: scripts/compare_embeddings.py

임베딩은 LLM 이 아니라 로컬 모델이라 비용이 없고, 같은 입력이면 같은 결과가 나온다.
"""
from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable

import numpy as np

from concepts.concept_map import Term

Encoder = Callable[[list[str]], np.ndarray]  # 글 목록 -> (n, d) 정규화된 벡터

# 후보 모델: 이름 -> 글 앞에 붙일 말 (e5 계열은 "query: " 를 붙이도록 학습됐다)
MODELS = {
    "jhgan/ko-sroberta-multitask": "",
    "intfloat/multilingual-e5-base": "query: ",
    "BAAI/bge-m3": "",
    "nlpai-lab/KURE-v1": "",
}

# 모델: scripts/compare_embeddings.py 비교 결과 (2026-11-23, 인과 사전 글 100개).
# KURE-v1 이 F1 0.689·정밀도 0.912 로 가장 높고, 기준금리 인상/인하 같은 반대말을 합치지 않았다. bge-m3 (0.676) 와 차이는 작다.
# 기준값: 처음엔 인과 사전에서 F1 최고였던 0.70 이었다. 2026-11-24 실제 카드 용어 26개로 돌리니 0.70 에서 묶인 7개 중
# 5개가 다른 개념이었다 (사람 검토: 등락률/등락 종목 수, 매출액/매출액 대비, 영업이익/당기순이익, 자사주 취득/기취득 자기주식,
# 시가총액/시가총액 비중). 다른 개념 쌍이 0.86 까지 나와서, 그보다 위인 0.90 으로 올리고 괄호만 다른 표기는
# concept_map.term_key 규칙으로 합친다. 정밀도를 앞에 두는 이유: 못 묶으면 칸이 둘로 남을 뿐이지만 잘못 묶으면 개념이 섞인다
# (튜터가 영업이익을 맞힌 사람을 당기순이익도 안다고 처리한다). 인과 사전에서 KURE-v1 은 0.80 이상에서 잘못 묶은 쌍이 0 이었다
DEFAULT_MODEL = "nlpai-lab/KURE-v1"
DEFAULT_THRESHOLD = 0.90
# 헷갈리는 쌍: 묶기에는 모자라지만 가까운 개념. 위 5쌍(0.725~0.860)이 바로 학습자가 헷갈리기 쉬운 쌍이라,
# 튜터의 "헷갈리는 쌍" 퀴즈 재료로 쓴다 (계획 1-3 "쌍은 개념 지도에서 임베딩이 가까운 개념끼리 자동으로")
CONFUSABLE_LOW = 0.70


def load_encoder(model_name: str) -> Encoder:
    """sentence-transformers 모델을 불러온다. 처음 한 번은 Hugging Face 에서 내려받는다 (~/.cache/huggingface)."""
    from sentence_transformers import SentenceTransformer  # 무거워서 쓸 때만 불러온다

    model = SentenceTransformer(model_name)
    prefix = MODELS.get(model_name, "")

    def encode(texts: list[str]) -> np.ndarray:
        return model.encode([prefix + t for t in texts], normalize_embeddings=True, convert_to_numpy=True)

    return encode


def similarity(vecs: np.ndarray) -> np.ndarray:
    """정규화된 벡터의 코사인 유사도 행렬."""
    return vecs @ vecs.T


def group_indices(sim: np.ndarray, threshold: float) -> list[list[int]]:
    """완전 연결로 묶는다. 묶음 안의 모든 쌍이 threshold 이상. 결과는 첫 번호 순, 묶음 안도 번호 순.
    가장 비슷한 두 묶음부터 합치고, 묶음끼리 유사도는 두 묶음 사이 가장 낮은 쌍의 값으로 갱신한다."""
    n = len(sim)
    s = np.array(sim, dtype=float, copy=True)
    np.fill_diagonal(s, -np.inf)
    members = {i: [i] for i in range(n)}
    while len(members) > 1:
        flat = int(np.argmax(s))  # 같은 값이면 앞 번호가 먼저 (돌릴 때마다 같다)
        i, j = divmod(flat, n)
        if s[i, j] < threshold:
            break
        i, j = min(i, j), max(i, j)
        s[i, :] = np.minimum(s[i, :], s[j, :])  # 완전 연결: 낮은 쪽
        s[:, i] = s[i, :]
        s[i, i] = -np.inf
        s[j, :] = -np.inf
        s[:, j] = -np.inf
        members[i] += members.pop(j)
    return sorted(sorted(g) for g in members.values())


def pair_scores(groups: list[list[int]], gold: list[str]) -> dict[str, float]:
    """쌍 단위 정밀도·재현율·F1. gold[i] 는 i 번 글의 정답 개념.
    정밀도: 묶인 쌍 중 정답도 같은 개념인 비율 (낮으면 다른 개념을 합쳤다)
    재현율: 정답이 같은 쌍 중 실제로 묶인 비율 (낮으면 같은 뜻을 못 묶었다)"""
    pred = {frozenset(p) for g in groups for p in combinations(g, 2)}
    true = {frozenset((a, b)) for a, b in combinations(range(len(gold)), 2) if gold[a] == gold[b]}
    hit = len(pred & true)
    p = hit / len(pred) if pred else 1.0
    r = hit / len(true) if true else 1.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f, "pred_pairs": len(pred), "true_pairs": len(true)}


@dataclass
class ConceptNode:
    label: str                                         # 대표 이름: 가장 많은 카드에 나온 용어 (같으면 먼저 나온 것)
    desc: str
    aliases: list[str] = field(default_factory=list)   # 나머지 용어
    card_ids: list[int] = field(default_factory=list)  # 묶인 용어들이 나온 카드 전부


def make_nodes(terms: list[Term], groups: list[list[int]]) -> list[ConceptNode]:
    nodes = []
    for g in groups:
        ts = [terms[i] for i in g]
        head = max(ts, key=lambda t: len(t.card_ids))  # max 는 같은 값이면 앞의 것을 고른다
        cards = sorted({c for t in ts for c in t.card_ids})
        nodes.append(ConceptNode(head.term, head.desc, [t.term for t in ts if t is not head], cards))
    return nodes


def confusable_pairs(nodes: list[ConceptNode], groups: list[list[int]], sim: np.ndarray,
                     low: float = CONFUSABLE_LOW, top: int = 3) -> dict[str, list[str]]:
    """노드마다 헷갈리기 쉬운 다른 노드 (대표 이름 → 대표 이름 목록, 가까운 순, 최대 top 개).
    두 노드의 유사도 = 두 묶음 사이 용어 쌍 중 가장 높은 값. low 이상이면 헷갈리는 쌍이다.
    따로 남은 노드끼리라 대부분 묶기 기준값보다 낮다. 기준값 이상인데 완전 연결 때문에 못 묶인 쌍도 헷갈리기 쉬워서 넣는다."""
    out: dict[str, list[tuple[float, str]]] = {}
    for a, b in combinations(range(len(groups)), 2):
        v = max(float(sim[i, j]) for i in groups[a] for j in groups[b])
        if v >= low:
            out.setdefault(nodes[a].label, []).append((v, nodes[b].label))
            out.setdefault(nodes[b].label, []).append((v, nodes[a].label))
    return {k: [n for _, n in sorted(vs, key=lambda x: (-x[0], x[1]))[:top]] for k, vs in out.items()}


def group_terms(terms: list[Term], encode: Encoder, threshold: float = DEFAULT_THRESHOLD) -> list[ConceptNode]:
    """③ 용어 목록 -> 개념 노드. 용어 글자만 임베딩한다 (설명은 카드마다 문체가 달라 유사도를 흔든다)."""
    if not terms:
        return []
    sim = similarity(encode([t.term for t in terms]))
    return make_nodes(terms, group_indices(sim, threshold))
