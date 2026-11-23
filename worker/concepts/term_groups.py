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

# 기본값: scripts/compare_embeddings.py 비교 결과 (2026-11-23, 인과 사전 글 100개).
# KURE-v1 기준 0.70 에서 F1 0.689·정밀도 0.912 로 가장 높고, 기준금리 인상/인하 같은 반대말을 합치지 않았다.
# bge-m3 (F1 0.676) 와 차이는 작다. 정밀도를 앞에 두는 이유: 못 묶으면 칸이 둘로 남을 뿐이지만 잘못 묶으면 개념이 섞인다
DEFAULT_MODEL = "nlpai-lab/KURE-v1"
DEFAULT_THRESHOLD = 0.70


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


def group_terms(terms: list[Term], encode: Encoder, threshold: float = DEFAULT_THRESHOLD) -> list[ConceptNode]:
    """③ 용어 목록 -> 개념 노드. 용어 글자만 임베딩한다 (설명은 카드마다 문체가 달라 유사도를 흔든다)."""
    if not terms:
        return []
    sim = similarity(encode([t.term for t in terms]))
    return make_nodes(terms, group_indices(sim, threshold))
