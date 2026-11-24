"""개념 지도 ③ 같은 뜻 묶기 (사람1, #198). 로컬 임베딩으로 "EPS" 와 "주당순이익" 을 한 개념 노드로 묶는다.

방법
- 용어마다 임베딩 벡터를 만들고 (정규화해서 내적 = 코사인 유사도), 유사도가 기준값 이상인 것끼리 묶는다
- 묶을 때는 "완전 연결(complete linkage)": 두 묶음을 합치려면 **모든 쌍**이 기준값 이상이어야 한다.
  한 쌍만 비슷해도 합치는 방식(단일 연결)은 "금리 인상 ~ 금리 ~ 금리 인하" 처럼 사슬로 이어져 반대말까지 합친다
- 기준값과 모델은 인과 사전 별칭(사람이 쓴 정답)으로 고른다: scripts/compare_embeddings.py

임베딩은 LLM 이 아니라 로컬 모델이라 비용이 없고, 같은 입력이면 같은 결과가 나온다.
"""
import csv
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
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
        aliases = [t.term for t in ts if t is not head]
        for t in ts:  # ② 에서 같은 뜻이라고 연결된 표기도 별칭으로 ("자기주식 취득" → 자사주 취득)
            aliases += [v for v in t.variants if v != head.term and v not in aliases]
        nodes.append(ConceptNode(head.term, head.desc, aliases, cards))
    return nodes


# ② 에서 LLM 이 "같은 뜻"이라고 한 쌍을 받아들이는 임베딩 하한. 묶기 기준(0.90)보다 낮다: LLM 판단과 임베딩 두 신호가
# 모두 같다고 할 때만 합치기 때문이다. 2026-11-24 실제 카드: 자기주식 취득/자사주 취득 0.893 (같음, 통과),
# 자기주식/자사주 취득 0.750 (LLM 이 같다고 했지만 가진 주식 / 사는 행동이라 다름, 거절)
SAME_AS_MIN = 0.80


def same_meaning(encode: Encoder, a: str, b: str, low: float = SAME_AS_MIN) -> bool:
    return float(similarity(encode([a, b]))[0, 1]) >= low


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


def confusable_candidates(nodes: list[ConceptNode], groups: list[list[int]], sim: np.ndarray,
                          low: float = CONFUSABLE_LOW, top: int = 3) -> list[tuple[int, int, float]]:
    """헷갈리는 이웃 후보 쌍 (a, b, 유사도), a < b, 유사도 높은 순. confusable_pairs 와 같은 기준으로
    어느 한쪽의 가까운 top 개에 드는 쌍만. 사람 검토(confusable_review.csv)를 거쳐 지도에 들어간다 (#228)."""
    near: dict[int, list[tuple[float, int]]] = {}
    score = {}
    for a, b in combinations(range(len(groups)), 2):
        v = max(float(sim[i, j]) for i in groups[a] for j in groups[b])
        if v >= low:
            score[(a, b)] = v
            near.setdefault(a, []).append((v, b))
            near.setdefault(b, []).append((v, a))
    keep = set()
    for k, vs in near.items():
        for _, other in sorted(vs, key=lambda x: (-x[0], nodes[x[1]].label))[:top]:
            keep.add((min(k, other), max(k, other)))
    return sorted(((a, b, round(score[(a, b)], 3)) for a, b in keep), key=lambda x: (-x[2], x[0], x[1]))


def name_index(nodes: list[ConceptNode]) -> dict[str, int]:
    """검토 파일의 이름 → 노드 번호. 대표 이름을 먼저, 그다음 별칭 (묶음의 대표 이름이 바뀌어도 예전 이름으로 찾게)."""
    idx = {n.label: k for k, n in enumerate(nodes)}
    for k, n in enumerate(nodes):
        for a in n.aliases:
            idx.setdefault(a, k)
    return idx


# --- 헷갈리는 이웃 사람 검토 (#228) ---
# 임베딩만으로는 글자 모양이 비슷한 엉뚱한 쌍(매출액 ↔ 시가총액, 거래량 ↔ 매출액)이 섞인다. 복습 문제·튜터의 "헷갈리는 쌍"
# 퀴즈에 그대로 쓰면 이상한 문제가 나와서, 사람이 keep 한 쌍만 지도에 넣는다. 빈칸(아직 안 봄)은 넣지 않는다
# (선수 관계와 다르다: 선수 관계는 다수결을 거쳤지만 이웃은 임베딩 하나뿐이다).
# 쌍은 순서 없이 한 줄이고, keep 이면 양쪽 방향 모두 헷갈리는 이웃이 된다.

CONFUSABLE_REVIEW_PATH = Path(__file__).with_name("confusable_review.csv")
CONFUSABLE_REVIEW_FIELDS = ["a", "b", "sim", "decision", "note"]


@dataclass
class ConfusableRow:
    a: str
    b: str
    sim: str = ""        # 임베딩 유사도. 사람이 직접 더한 줄은 빈칸이어도 된다
    decision: str = ""   # keep / drop / 빈칸: 아직 안 봄 (지도에 안 넣음)
    note: str = ""


def load_confusable_review(path: Path = CONFUSABLE_REVIEW_PATH) -> list[ConfusableRow]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [ConfusableRow(**{k: (r.get(k) or "").strip() for k in CONFUSABLE_REVIEW_FIELDS})
                for r in csv.DictReader(f)]


def save_confusable_review(rows: list[ConfusableRow], path: Path = CONFUSABLE_REVIEW_PATH) -> Path:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # 엑셀에서 한글이 안 깨지게 BOM
        w = csv.DictWriter(f, fieldnames=CONFUSABLE_REVIEW_FIELDS)
        w.writeheader()
        w.writerows(asdict(r) for r in rows)
    return path


def merge_confusable(rows: list[ConfusableRow], nodes: list[ConceptNode],
                     cands: list[tuple[int, int, float]]) -> int:
    """파일에 없는 후보 쌍을 빈칸 줄로 더한다 (rows 를 바꾼다). 더한 줄 수. 이미 있는 줄(drop 포함)은 그대로 둔다."""
    idx = name_index(nodes)
    have = {frozenset((idx.get(r.a, r.a), idx.get(r.b, r.b))) for r in rows}
    added = 0
    for a, b, v in cands:
        if frozenset((a, b)) not in have:
            rows.append(ConfusableRow(nodes[a].label, nodes[b].label, f"{v:.3f}"))
            have.add(frozenset((a, b)))
            added += 1
    return added


def reviewed_confusable(rows: list[ConfusableRow], nodes: list[ConceptNode]
                        ) -> tuple[list[tuple[int, int, float | None]], list[ConfusableRow]]:
    """keep 한 쌍 (a, b, 유사도) 와 지도에 없는 이름이 있는 keep 줄. 같은 쌍이 여러 줄이면 drop 이 하나라도 있으면 뺀다."""
    idx = name_index(nodes)
    by_pair: dict[frozenset, list[ConfusableRow]] = {}
    missing = []
    for r in rows:
        if r.a not in idx or r.b not in idx:
            if r.decision == "keep":
                missing.append(r)
            continue
        if idx[r.a] != idx[r.b]:
            by_pair.setdefault(frozenset((idx[r.a], idx[r.b])), []).append(r)
    out = []
    for pair, rs in by_pair.items():
        decided = {r.decision for r in rs}
        if "keep" in decided and "drop" not in decided:
            a, b = sorted(pair)
            sims = [float(r.sim) for r in rs if r.sim]
            out.append((a, b, max(sims) if sims else None))
    return sorted(out, key=lambda x: (-(x[2] or 0), x[0], x[1])), missing


def confusable_map(nodes: list[ConceptNode], pairs: list[tuple[int, int, float | None]]) -> dict[str, list[str]]:
    """쌍 → 튜터가 읽는 모양 {대표 이름: 헷갈리는 이웃들 (유사도 높은 순)}. 양쪽 방향."""
    out: dict[str, list[tuple[float, str]]] = {}
    for a, b, v in pairs:
        out.setdefault(nodes[a].label, []).append((v or 0, nodes[b].label))
        out.setdefault(nodes[b].label, []).append((v or 0, nodes[a].label))
    return {k: [n for _, n in sorted(vs, key=lambda x: (-x[0], x[1]))] for k, vs in out.items()}


def group_terms(terms: list[Term], encode: Encoder, threshold: float = DEFAULT_THRESHOLD) -> list[ConceptNode]:
    """③ 용어 목록 -> 개념 노드. 용어 글자만 임베딩한다 (설명은 카드마다 문체가 달라 유사도를 흔든다)."""
    if not terms:
        return []
    sim = similarity(encode([t.term for t in terms]))
    return make_nodes(terms, group_indices(sim, threshold))
