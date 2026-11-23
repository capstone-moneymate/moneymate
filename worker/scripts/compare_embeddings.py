"""개념 지도 ③ 임베딩 모델·기준값 고르기 (사람1, #198). 인과 사전(db/seeds/concepts.csv)의 이름·별칭을 정답으로 쓴다.
사람이 쓴 "같은 개념의 다른 표현" 묶음이라, 임베딩이 이걸 다시 묶어 내는지로 모델을 비교한다.
"기준금리 인상/인하/동결", "자사주 취득/소각" 처럼 글자는 비슷하고 뜻은 다른 반례가 들어 있다.

실행 (worker/ 에서, sentence-transformers 필요):
    python -m scripts.compare_embeddings                              # 후보 모델 전부
    python -m scripts.compare_embeddings jhgan/ko-sroberta-multitask   # 하나만
결과는 화면과 logs/concept_map/embedding_compare.json 에 남는다.

주의: 기준값을 같은 정답 데이터로 고르므로 이 점수는 실제보다 좋게 나온다 (데이터가 작아 따로 떼어 둘 여유가 없다).
모델끼리 비교하는 용도로 쓰고, 카드 용어에 적용한 결과는 사람이 한 번 훑어본다.
"""
import csv
import json
import sys
import time
from itertools import combinations

import numpy as np

from concepts.concept_map import OUT_DIR, term_key
from concepts.graph import SEEDS
from concepts.term_groups import MODELS, group_indices, load_encoder, pair_scores, similarity

THRESHOLDS = [round(x, 2) for x in np.arange(0.50, 0.96, 0.05)]


def load_gold() -> tuple[list[str], list[str]]:
    """(글, 정답 개념 id). 띄어쓰기·대소문자만 다른 중복은 처음 것만 (① 에서 이미 합쳐지는 경우라 빼도 된다)."""
    texts, gold, seen = [], [], set()
    with open(SEEDS / "concepts.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            for t in [r["name"], *r["aliases"].split(";")]:
                t = t.strip()
                if t and term_key(t) not in seen:
                    seen.add(term_key(t))
                    texts.append(t)
                    gold.append(r["id"])
    return texts, gold


def mistakes(groups: list[list[int]], texts: list[str], gold: list[str], sim: np.ndarray, top: int = 10) -> dict:
    """잘못 합친 쌍(다른 개념인데 묶음)과 놓친 쌍(같은 개념인데 안 묶음). 유사도가 헷갈리는 순으로."""
    same_group = {frozenset(p) for g in groups for p in combinations(g, 2)}
    wrong, missed = [], []
    for a, b in combinations(range(len(texts)), 2):
        pair = (texts[a], texts[b], round(float(sim[a, b]), 3))
        if frozenset((a, b)) in same_group and gold[a] != gold[b]:
            wrong.append(pair)
        elif frozenset((a, b)) not in same_group and gold[a] == gold[b]:
            missed.append(pair)
    wrong.sort(key=lambda p: -p[2])
    missed.sort(key=lambda p: p[2])
    return {"wrong": wrong[:top], "missed": missed[:top], "wrong_count": len(wrong), "missed_count": len(missed)}


def evaluate(model_name: str, texts: list[str], gold: list[str]) -> dict:
    start = time.perf_counter()
    encode = load_encoder(model_name)
    loaded = time.perf_counter()
    sim = similarity(encode(texts))
    encoded = time.perf_counter()
    sweep = []
    for th in THRESHOLDS:
        s = pair_scores(group_indices(sim, th), gold)
        sweep.append({"threshold": th, **{k: round(v, 3) for k, v in s.items()}})
    best = max(sweep, key=lambda r: (r["f1"], r["precision"]))  # F1 이 같으면 덜 합치는(정밀도 높은) 쪽
    return {
        "model": model_name,
        "load_sec": round(loaded - start, 1),
        "encode_sec": round(encoded - loaded, 2),
        "best": best,
        "sweep": sweep,
        "mistakes": mistakes(group_indices(sim, best["threshold"]), texts, gold, sim),
    }


def main(argv: list[str]) -> None:
    models = argv or list(MODELS)
    texts, gold = load_gold()
    print(f"정답 데이터: 글 {len(texts)}개, 개념 {len(set(gold))}개")
    results = []
    for name in models:
        print(f"\n== {name}")
        r = evaluate(name, texts, gold)
        results.append(r)
        print(f"   불러오기 {r['load_sec']}초, 임베딩 {r['encode_sec']}초")
        print("   기준값  정밀도  재현율  F1")
        for row in r["sweep"]:
            mark = "  <- 최고" if row is r["best"] else ""
            print(f"   {row['threshold']:.2f}    {row['precision']:.3f}   {row['recall']:.3f}   {row['f1']:.3f}{mark}")
        m = r["mistakes"]
        print(f"   잘못 합침 {m['wrong_count']}쌍: " + ", ".join(f"{a}={b}({s})" for a, b, s in m["wrong"][:5]))
        print(f"   놓침 {m['missed_count']}쌍: " + ", ".join(f"{a}/{b}({s})" for a, b, s in m["missed"][:5]))

    print("\n== 요약 (최고 F1 기준)")
    for r in sorted(results, key=lambda r: -r["best"]["f1"]):
        b = r["best"]
        print(f"   {r['model']:<32} 기준 {b['threshold']:.2f}  F1 {b['f1']:.3f}  정밀도 {b['precision']:.3f}  재현율 {b['recall']:.3f}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "embedding_compare.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
