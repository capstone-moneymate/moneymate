"""개념 지도를 DB 에 넣는다 (사람1, #224). build_map 이 만든 logs/concept_map/concept_map.json → 사람2의 009 테이블.
    concept_nodes       노드 (이름 label 으로 맞춘다)
    concept_node_cards  노드가 나온 카드
    concept_prereq      선수 관계

다시 돌려도 지도와 같아진다 (중복 없음):
- 노드: 이름이 같으면 고친다(설명·별칭). 지도에서 빠진 노드는 **지우지 않는다**. 지우면 user_concept_state 가 함께
  지워져 학습 기록이 사라진다 (ON DELETE CASCADE). 개수만 알려 준다.
  사람2의 update_causal 은 본 문제 답에서 탭 1 개념 노드를 스스로 만든다 (이름 = concepts.name). 그 노드도 같은 표에 있다.
- 카드 연결: 지도 노드의 카드 연결은 지도대로 바꾼다. DB 에 없는 카드는 건너뛴다.
- 선수 관계: concept_prereq 는 지도만 쓰는 표라 통째로 지도대로 바꾼다.
  사람이 keep / add 한 연결은 지도에서 5표(prereq_votes.HUMAN_VOTES, 순환을 끊을 때만 쓰는 값)라서,
  표의 규칙 total >= votes 에 맞게 4 / 4 로 넣는다. 사람이 정했는지는 검토 파일(prereq_review.csv)에 있다.
- 탭 1 단어 짝짓기(causal_id): 탭 1 단어 목록(concepts 표)에서 **개념 이름·별칭만** 읽는다. 인과 화살표(causal_edges)는
  읽지도 쓰지도 않고, concepts 표도 고치지 않는다. 노드 이름·별칭이 탭 1 개념의 이름·별칭과 글자가 같을 때만 짝짓는다
  (띄어쓰기·대소문자·괄호 무시, term_key). 한 노드가 여러 개념에, 또는 한 개념이 여러 노드에 걸리면 애매해서 잇지 않는다. 이미 다른 노드가 가진
  개념은 빼앗지 않는다 (causal_id 는 UNIQUE). 이미 짝지어진 노드는 그대로 둔다. 짝지어야 본 문제 답(update_causal)이
  개념 지도의 알 확률을 고친다 (본 문제와 튜터가 같은 개념의 알 확률 하나를 함께 쓴다).

실행 (worker/ 에서): python -m concepts.load_map            # logs/concept_map/concept_map.json
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from concepts.concept_map import OUT_DIR, term_key


def causal_links(nodes: list[dict], concepts: list[tuple[str, str, list[str]]]) -> tuple[dict[str, str], list[str]]:
    """노드 label → 탭 1 개념 id (이름·별칭 글자가 같은 것만. 인과 화살표는 안 본다). (연결, 애매해서 안 이은 노드 label) 을 돌려준다.
    concepts: (id, name, aliases)."""
    by_key: dict[str, set[str]] = defaultdict(set)
    for cid, name, aliases in concepts:
        for k in {term_key(name), *(term_key(a) for a in aliases or [])}:
            if k:
                by_key[k].add(cid)
    hits = {}
    for n in nodes:
        keys = {term_key(n["label"]), *(term_key(a) for a in n.get("aliases") or [])}
        found = set().union(*(by_key.get(k, set()) for k in keys if k))
        if found:
            hits[n["label"]] = found
    owners: dict[str, list[str]] = defaultdict(list)
    for label, found in hits.items():
        for cid in found:
            owners[cid].append(label)
    links, unclear = {}, []
    for label, found in hits.items():
        if len(found) == 1 and len(owners[next(iter(found))]) == 1:
            links[label] = next(iter(found))
        else:
            unclear.append(label)
    return links, unclear


def load(conn, result: dict) -> dict:
    """result = concept_map.json 내용. 커밋하지 않는다 (부르는 쪽이 with get_conn() 으로 묶는다). 개수 요약을 돌려준다."""
    nodes = result["nodes"]
    labels = [n["label"] for n in nodes]
    concepts = conn.execute("SELECT id, name, aliases FROM concepts").fetchall()
    links, unclear = causal_links(nodes, concepts)
    held = dict(conn.execute("SELECT causal_id, label FROM concept_nodes WHERE causal_id IS NOT NULL").fetchall())
    taken = [lb for lb, cid in links.items() if held.get(cid, lb) != lb]   # 다른 노드가 이미 가진 개념
    for lb in taken:
        del links[lb]

    ids = {}
    for n in nodes:
        ids[n["label"]] = conn.execute(
            """INSERT INTO concept_nodes (label, description, aliases, causal_id) VALUES (%s, %s, %s, %s)
               ON CONFLICT (label) DO UPDATE SET
                   description = COALESCE(NULLIF(EXCLUDED.description, ''), concept_nodes.description),
                   aliases = concept_nodes.aliases
                             || ARRAY(SELECT a FROM unnest(EXCLUDED.aliases) a WHERE a <> ALL (concept_nodes.aliases)),
                   causal_id = COALESCE(concept_nodes.causal_id, EXCLUDED.causal_id),
                   updated_at = now()
               RETURNING id""",
            (n["label"], n.get("desc") or None, n.get("aliases") or [], links.get(n["label"])),
        ).fetchone()[0]

    node_ids = list(ids.values())
    want = sorted({c for n in nodes for c in n.get("card_ids") or []})
    have = {r[0] for r in conn.execute("SELECT id FROM cards WHERE id = ANY(%s)", (want,)).fetchall()}
    conn.execute("DELETE FROM concept_node_cards WHERE node_id = ANY(%s)", (node_ids,))
    card_rows = [(ids[n["label"]], c) for n in nodes for c in sorted(set(n.get("card_ids") or [])) if c in have]
    if card_rows:
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO concept_node_cards (node_id, card_id) VALUES (%s, %s)", card_rows)

    by_file_id = {n["id"]: ids[n["label"]] for n in nodes}
    prereq_rows = [(by_file_id[e["pre_id"]], by_file_id[e["post_id"]], min(e["votes"], e["total"]), e["total"])
                   for e in result["prereqs"]]
    conn.execute("DELETE FROM concept_prereq")
    if prereq_rows:
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO concept_prereq (pre_id, post_id, votes, total) VALUES (%s, %s, %s, %s)",
                            prereq_rows)

    linked = dict(conn.execute("SELECT label, causal_id FROM concept_nodes WHERE label = ANY(%s) AND causal_id IS NOT NULL",
                               (labels,)).fetchall())
    stale = [r[0] for r in conn.execute(
        "SELECT label FROM concept_nodes WHERE label <> ALL(%s) AND causal_id IS NULL ORDER BY id", (labels,)).fetchall()]
    return {
        "nodes": len(nodes),
        "cards": len(card_rows),
        "cards_missing": sorted(set(want) - have),
        "prereqs": len(prereq_rows),
        "causal_linked": linked,             # 지도 노드 중 탭 1 단어와 짝지어진 것 (이번에 짝지은 것 + 원래 짝지어져 있던 것)
        "causal_unclear": sorted(unclear),   # 여러 개념·여러 노드에 걸려 안 이음
        "causal_taken": sorted(taken),       # 그 개념을 이미 다른 노드가 가져서 안 이음
        "stale_nodes": stale,                # DB 에만 있고 지도에 없는 노드 (지우지 않음). 탭 1 개념 노드는 뺀 수
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="개념 지도를 DB 에 넣기")
    parser.add_argument("--path", type=Path, default=OUT_DIR / "concept_map.json")
    args = parser.parse_args()
    result = json.loads(args.path.read_text(encoding="utf-8"))

    from db import get_conn

    with get_conn() as conn:  # 끝까지 성공하면 커밋, 중간에 실패하면 전부 취소
        s = load(conn, result)
    print(f"개념 지도 DB 넣기: 노드 {s['nodes']}개, 카드 연결 {s['cards']}개 (DB 에 없는 카드 {len(s['cards_missing'])}개), "
          f"선수 관계 {s['prereqs']}개")
    print(f"   탭 1 단어 짝짓기 (이름만, 인과 화살표 안 씀) {len(s['causal_linked'])}개: {s['causal_linked']}")
    if s["causal_unclear"] or s["causal_taken"]:
        print(f"   안 짝지음: 애매 {s['causal_unclear']}, 다른 노드가 가짐 {s['causal_taken']}")
    if s["stale_nodes"]:
        print(f"   지도에 없는 DB 노드 {len(s['stale_nodes'])}개 (학습 기록 보호로 지우지 않음): {s['stale_nodes']}")


if __name__ == "__main__":
    main()
