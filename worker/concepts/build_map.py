"""개념 지도 한 번에 만들기 (사람1, #198). ① 재료 → ② 용어 뽑기 → ③ 같은 뜻 묶기 → ④ 선수 관계 다수결 → ⑤ 저장.
각 단계 코드는 concept_map.py (①②), term_groups.py (③), prereq_votes.py (④) 에 있고, 여기서는 잇기만 한다.

⑤ 저장: 사람2의 009 마이그레이션(concept_nodes, concept_prereq) 전이라 DB 대신 파일로 남긴다 (Git 에 안 올라감).
    logs/concept_map/concept_map.json   노드·선수 관계·설정·개수. 테이블이 생기면 이 파일을 그대로 넣는다
    logs/concept_map/groups_review.tsv  두 용어 이상 묶인 노드만. 사람이 훑어보고 잘못 묶인 줄에 표시한다

실행 (worker/ 에서, ③ 은 pip install -e ".[embed]" 필요):
    python -m concepts.build_map                       # ①③ 만 (LLM 호출 없음, 비용 0)
    python -m concepts.build_map --extract --prereq    # ①②③④ 전부 (Haiku 비용 발생)
    python -m concepts.build_map --prereq --max-pairs 20   # ④ 를 20쌍만 시험
"""
import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np

from concepts import prereq_votes as pv
from concepts import term_groups as tg
from concepts.concept_map import OUT_DIR, Materials, extract_terms, gather


def node_id(k: int) -> str:
    """파일 안에서 쓰는 노드 id (c001, c002, ...). DB id 는 009 마이그레이션에서 새로 매긴다."""
    return f"c{k + 1:03d}"


def review_rows(terms, groups: list[list[int]], sim: np.ndarray) -> list[dict]:
    """두 용어 이상 묶인 노드마다: 대표 이름, 묶인 용어, 묶음 안 가장 낮은 유사도. 낮은 것부터 (의심스러운 것부터 보게)."""
    rows = []
    for k, g in enumerate(groups):
        if len(g) < 2:
            continue
        low = min(float(sim[a, b]) for a, b in combinations(g, 2))
        rows.append({"id": node_id(k), "members": [terms[i].term for i in g], "min_sim": round(low, 3)})
    return sorted(rows, key=lambda r: (r["min_sim"], r["id"]))


def run(m: Materials, encode: tg.Encoder, *, threshold: float = tg.DEFAULT_THRESHOLD, prereq: bool = False,
        max_pairs: int = pv.MAX_PAIRS, top_k: int = pv.TOP_K) -> dict:
    """③④ 를 돌려 저장할 결과를 만든다 (①② 는 m 에 이미 들어 있다). DB·파일을 건드리지 않는다."""
    terms = m.terms
    if terms:
        term_sim = tg.similarity(encode([t.term for t in terms]))
        groups = tg.group_indices(term_sim, threshold)
    else:
        term_sim, groups = np.zeros((0, 0)), []
    nodes = tg.make_nodes(terms, groups)

    edges, stats = [], None
    if prereq and len(nodes) > 1:
        node_sim = tg.similarity(encode([n.label for n in nodes]))
        pairs = pv.candidate_pairs(nodes, node_sim, top_k=top_k, max_pairs=max_pairs)
        edges, stats = pv.build_prereqs(nodes, pairs)

    return {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settings": {"threshold": threshold, "votes": pv.VOTES, "top_k": top_k, "max_pairs": max_pairs},
        "counts": {
            "terms": len(terms),
            "terms_from_source": sum(t.origin == "source" for t in terms),
            "nodes": len(nodes),
            "merged_nodes": sum(len(g) > 1 for g in groups),
            "prereqs": len(edges),
        },
        "prereq_stats": stats,
        "nodes": [{"id": node_id(k), **asdict(n)} for k, n in enumerate(nodes)],
        "prereqs": [{"pre_id": node_id(e.pre), "post_id": node_id(e.post), "votes": e.votes, "total": e.total}
                    for e in edges],
        "review": review_rows(terms, groups, term_sim),
    }


def save(result: dict, out_dir: Path = OUT_DIR) -> tuple[Path, Path]:
    """⑤ concept_map.json 과 groups_review.tsv. 검토 표의 '잘못' 칸은 비워 두고 사람이 채운다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    main = out_dir / "concept_map.json"
    main.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    review = out_dir / "groups_review.tsv"
    lines = ["id\t최저유사도\t묶인 용어\t잘못(O 표시)"]
    lines += [f"{r['id']}\t{r['min_sim']}\t{' | '.join(r['members'])}\t" for r in result["review"]]
    review.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")  # 엑셀에서 한글이 안 깨지게 BOM
    return main, review


def summary(result: dict) -> str:
    """완료 기준 로그: 몇 개가 만들어졌는지."""
    c, s = result["counts"], result["prereq_stats"]
    text = (f"개념 지도: 용어 {c['terms']}개 (② 에서 {c['terms_from_source']}개) → 노드 {c['nodes']}개 "
            f"(두 용어 이상 묶임 {c['merged_nodes']}개), 선수 관계 {c['prereqs']}개")
    if s:
        text += f"\n   ④ 후보 {s['pairs']}쌍, 호출 {s['calls']}회, 연결 {s['edges']} / 표 갈림 {s['split']} / 관계 없음 {s['none']}"
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="개념 지도 한 번에 만들기")
    parser.add_argument("--extract", action="store_true", help="② LLM 용어 뽑기 (비용 발생)")
    parser.add_argument("--prereq", action="store_true", help="④ 선수 관계 다수결 (비용 발생)")
    parser.add_argument("--max-pairs", type=int, default=pv.MAX_PAIRS, help="④ 후보 쌍 상한")
    parser.add_argument("--threshold", type=float, default=tg.DEFAULT_THRESHOLD, help="③ 묶기 기준값")
    parser.add_argument("--model", default=tg.DEFAULT_MODEL, help="③ 임베딩 모델")
    args = parser.parse_args()

    from db import get_conn

    with get_conn() as conn:
        m = gather(conn)
    if args.extract:
        extract_terms(m)
    result = run(m, tg.load_encoder(args.model), threshold=args.threshold, prereq=args.prereq,
                 max_pairs=args.max_pairs)
    result["settings"]["model"] = args.model
    main_path, review_path = save(result)
    print(summary(result))
    print(f"   저장: {main_path}\n   검토 표: {review_path}")


if __name__ == "__main__":
    main()
