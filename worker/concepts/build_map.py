"""개념 지도 한 번에 만들기 (사람1, #198). ① 재료 → ② 용어 뽑기 → ③ 같은 뜻 묶기 → ④ 선수 관계 다수결 → ⑤ 저장.
각 단계 코드는 concept_map.py (①②), term_groups.py (③), prereq_votes.py (④) 에 있고, 여기서는 잇기만 한다.

사람 검토 파일 (Git 에 올림. 지도의 정답지): concepts/term_review.csv (②), concepts/prereq_review.csv (④).
LLM 을 다시 돌리면 새 결과만 빈칸 줄로 더해지고, 사람이 decision 을 채운다 (#203).

⑤ 저장: 사람2의 009 테이블에 넣기 전까지 파일로 남긴다 (logs/ 라 Git 에 안 올라감).
    logs/concept_map/concept_map.json   노드·선수 관계·설정·개수. 테이블이 생기면 이 파일을 그대로 넣는다
    logs/concept_map/groups_review.tsv  두 용어 이상 묶인 노드만. 사람이 훑어보고 잘못 묶인 줄에 표시한다
    logs/concept_map/prereq_review.tsv  선수 관계와 순환으로 뺀 연결

실행 (worker/ 에서, ③ 은 pip install -e ".[embed]" 필요):
    python -m concepts.build_map                       # LLM 호출 없음, 비용 0. ①③ + 두 검토 파일로 같은 지도
    python -m concepts.build_map --extract --prereq    # ②④ 를 다시 돌림 (Haiku 비용 발생)
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
from concepts.prereq_check import break_cycles
from concepts import term_groups as tg
from concepts.concept_map import (OUT_DIR, REVIEW_PATH, Materials, apply_review, extract_terms, gather,
                                  load_review, save_review)


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
        max_pairs: int = pv.MAX_PAIRS, top_k: int = pv.TOP_K,
        prereq_review: list[pv.PrereqRow] | None = None) -> dict:
    """③④ 를 돌려 저장할 결과를 만든다 (①② 는 m 에 이미 들어 있다). DB·파일을 건드리지 않는다.
    prereq_review 를 주면 선수 관계는 그 검토 줄에서 만든다 (drop 만 뺌). prereq=True 면 새 LLM 연결을 빈칸 줄로 더한다
    (prereq_review 를 바꾼다. 저장은 부른 쪽이). 주지 않으면 LLM 결과를 그대로 쓴다."""
    terms = m.terms
    if terms:
        term_sim = tg.similarity(encode([t.term for t in terms]))
        groups = tg.group_indices(term_sim, threshold)
    else:
        term_sim, groups = np.zeros((0, 0)), []
    nodes = tg.make_nodes(terms, groups)
    confusable = tg.confusable_pairs(nodes, groups, term_sim) if terms else {}

    edges, stats, removed, missing = [], None, [], []
    if prereq and len(nodes) > 1:
        node_sim = tg.similarity(encode([n.label for n in nodes]))
        pairs = pv.candidate_pairs(nodes, node_sim, top_k=top_k, max_pairs=max_pairs)
        edges, stats = pv.build_prereqs(nodes, pairs)
        if prereq_review is not None:
            stats["new_review_rows"] = pv.merge_llm_edges(prereq_review, nodes, edges)
    if prereq_review is not None:
        edges, missing_rows = pv.reviewed_edges(prereq_review, nodes)
        missing = [{"pre": r.pre, "post": r.post, "decision": r.decision} for r in missing_rows]
    if edges:
        # 순환 검사 (#199 prereq.dl): 순환 위 연결 중 표가 가장 적은 것부터 하나씩 뺀다
        checked = break_cycles([(node_id(e.pre), node_id(e.post), e.votes) for e in edges])
        removed = [{"pre_id": a, "post_id": b, "votes": v} for a, b, v in checked.removed]
        gone = {(r["pre_id"], r["post_id"]) for r in removed}
        edges = [e for e in edges if (node_id(e.pre), node_id(e.post)) not in gone]

    return {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settings": {"threshold": threshold, "confusable_low": tg.CONFUSABLE_LOW, "votes": pv.VOTES,
                     "top_k": top_k, "max_pairs": max_pairs},
        "counts": {
            "terms": len(terms),
            "terms_from_source": sum(t.origin == "source" for t in terms),
            "nodes": len(nodes),
            "merged_nodes": sum(len(g) > 1 for g in groups),
            "prereqs": len(edges),
            "confusable_nodes": len(confusable),
        },
        "prereq_stats": stats,
        "nodes": [{"id": node_id(k), **asdict(n)} for k, n in enumerate(nodes)],
        "prereqs": [{"pre_id": node_id(e.pre), "post_id": node_id(e.post), "votes": e.votes, "total": e.total}
                    for e in edges],
        "prereqs_removed_for_cycles": removed,
        "prereq_review_missing": missing,  # 검토 파일에 있지만 지금 지도에 없는 이름 (용어가 바뀌었을 때 확인)
        "confusable": confusable,  # 튜터의 "헷갈리는 쌍" 퀴즈 재료 (대표 이름 → 가까운 대표 이름들)
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
    if result["prereqs"] or result.get("prereqs_removed_for_cycles"):  # 선수 관계도 사람이 훑어볼 수 있게
        name = {n["id"]: n["label"] for n in result["nodes"]}
        pl = ["먼저\t다음\t표\t잘못(O 표시)"]
        pl += [f"{name[e['pre_id']]}\t{name[e['post_id']]}\t{e['votes']}/{e['total']}\t" for e in result["prereqs"]]
        pl += [f"{name[e['pre_id']]}\t{name[e['post_id']]}\t{e['votes']}\t순환이라 뺌"
               for e in result.get("prereqs_removed_for_cycles", [])]
        (out_dir / "prereq_review.tsv").write_text("\n".join(pl) + "\n", encoding="utf-8-sig")
    return main, review


def summary(result: dict) -> str:
    """완료 기준 로그: 몇 개가 만들어졌는지."""
    c, s = result["counts"], result["prereq_stats"]
    text = (f"개념 지도: 용어 {c['terms']}개 (② 에서 {c['terms_from_source']}개) → 노드 {c['nodes']}개 "
            f"(두 용어 이상 묶임 {c['merged_nodes']}개), 선수 관계 {c['prereqs']}개, "
            f"헷갈리는 이웃이 있는 노드 {c['confusable_nodes']}개")
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
    encode = tg.load_encoder(args.model)
    review = load_review()
    a = apply_review(m, review)  # 사람이 keep / same 으로 정한 ② 용어 (LLM 없음)
    pending = sum(1 for r in review if not r.decision)
    print(f"② 검토 반영: keep {a['keep']}개, same {a['same']}개 (아직 안 본 후보 {pending}개, {REVIEW_PATH.name})")
    if args.extract:
        s = extract_terms(m, same_check=lambda x, y: tg.same_meaning(encode, x, y), review=review)
        save_review(review)
        print(f"② 뽑기: 카드 {s['cards']}장, 새 후보 {s['candidates']}개 (그중 같은 뜻 자동 same "
              f"{s['candidates_same']}개, 같은 뜻 거절 {s['same_rejected']}개), 사람이 뺀 용어가 다시 나옴 "
              f"{s['dropped_by_review']}개, 코드가 버림 {s['dropped']}개")
        print(f"   → {REVIEW_PATH} 의 decision 칸을 채워 주세요 (keep / drop / same)")
    prereq_review = pv.load_prereq_review()
    result = run(m, encode, threshold=args.threshold, prereq=args.prereq, max_pairs=args.max_pairs,
                 prereq_review=prereq_review)
    result["settings"]["model"] = args.model
    if args.prereq:
        pv.save_prereq_review(prereq_review)
        print(f"④ 새 연결 {result['prereq_stats']['new_review_rows']}개를 {pv.PREREQ_REVIEW_PATH.name} 에 빈칸으로 더함 "
              f"(keep / drop 을 적어 주세요)")
    decided = sum(1 for r in prereq_review if r.decision)
    print(f"④ 검토 반영: {len(prereq_review)}줄 중 사람이 정한 것 {decided}개, "
          f"지도에 없는 이름 {len(result['prereq_review_missing'])}개 ({pv.PREREQ_REVIEW_PATH.name})")
    main_path, review_path = save(result)
    print(summary(result))
    print(f"   저장: {main_path}\n   검토 표: {review_path}")


if __name__ == "__main__":
    main()
