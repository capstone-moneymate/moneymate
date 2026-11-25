"""개념 지도를 DB 에 넣는다 (사람1, #224). build_map 이 만든 logs/concept_map/concept_map.json → 사람2의 009 테이블.
    concept_nodes       노드 (이름 label 으로 맞춘다)
    concept_node_cards  노드가 나온 카드
    concept_prereq      선수 관계
    concept_confusable  헷갈리는 이웃 (012, #228). 사람이 keep 한 쌍만, 한 줄 한 방향이라 쌍마다 두 줄

다시 돌려도 지도와 같아진다 (중복 없음):
- 노드: 이름이 같으면 고친다(설명·별칭). 지도에서 빠진 노드는 **지우지 않는다**. 지우면 user_concept_state 가 함께
  지워져 학습 기록이 사라진다 (ON DELETE CASCADE). 개수만 알려 준다.
  사람2의 update_causal 은 본 문제 답에서 탭 1 개념 노드를 스스로 만든다 (이름 = concepts.name). 그 노드도 같은 표에 있다.
  예외: 이름을 바꾸거나 합친 옛 노드(이름이 지도 노드의 별칭)는 학습 기록을 새 노드로 옮긴 뒤 지운다 (absorb_renamed, #262).
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


def absorb_renamed(conn, nodes: list[dict], ids: dict[str, int]) -> dict[str, str]:
    """지도에서 이름을 바꾸거나 합친 옛 노드를 새 노드로 옮기고 지운다 (#262). {옛 이름: 새 이름} 을 돌려준다.
    옛 노드 = DB 에만 있고, 이름이 지도 노드의 별칭과 같은 노드 (build_map 의 same 합치기가 옛 이름을 별칭으로 남긴다).
    그대로 두면 튜터가 카드 용어를 맞출 때 옛 노드를 먼저 잡아 합친 의미가 없어진다 (tutor.agent.card_targets).
    학습 기록은 옮긴다: 답·퀴즈는 새 노드로, 사용자 상태는 새 노드에 그 사용자 줄이 없을 때만 옮기고 둘 다 있으면
    더 최근에 고친 줄을 남긴다. 탭 1 단어 짝(causal_id)이 있는 옛 노드는 건드리지 않는다 (본 문제 답이 그 노드를 쓴다).
    별칭이 지도 노드 둘 이상에 걸리면 옮기지 않는다. 옮길 게 있으면 user_concept_state 쓰기를 커밋까지 막는다 (#263 리뷰)."""
    owners: dict[str, set[str]] = defaultdict(set)
    for n in nodes:
        for a in n.get("aliases") or []:
            if term_key(a) != term_key(n["label"]):
                owners[term_key(a)].add(n["label"])
    # 별칭 하나가 노드 둘 이상에 걸리면 어디로 옮길지 사람이 정한 게 아니라 옮기지 않는다 (탭 1 짝짓기와 같은 규칙)
    alias_owner = {k: next(iter(v)) for k, v in owners.items() if len(v) == 1}
    labels = [n["label"] for n in nodes]
    moved = {}
    olds = conn.execute(
        "SELECT id, label FROM concept_nodes WHERE label <> ALL(%s) AND causal_id IS NULL ORDER BY id", (labels,)).fetchall()
    absorb_ids = [i for i, lb in olds if term_key(lb) in alias_owner]
    if absorb_ids:
        # 잠금 순서를 복습 답(learner.review.answer: 퀴즈 줄 FOR UPDATE → user_concept_state)과 같게: 퀴즈 줄 먼저 (#263 리뷰)
        conn.execute("SELECT 1 FROM concept_quizzes WHERE node_id = ANY(%s) FOR UPDATE", (absorb_ids,))
        # 옮기는 사이에 학습 기록이 써지면(다른 연결의 답) 최신 기록을 지울 수 있어 커밋까지 쓰기를 막는다. 읽기는 된다
        conn.execute("LOCK TABLE user_concept_state IN SHARE ROW EXCLUSIVE MODE")
    for old_id, old_label in olds:
        new_label = alias_owner.get(term_key(old_label))
        if new_label is None:
            continue
        new_id = ids[new_label]
        conn.execute("UPDATE concept_answers SET node_id = %s WHERE node_id = %s", (new_id, old_id))
        conn.execute("UPDATE concept_quizzes SET node_id = %s WHERE node_id = %s", (new_id, old_id))
        conn.execute(  # 둘 다 있으면 오래된 쪽을 지운다
            """DELETE FROM user_concept_state o USING user_concept_state n
                WHERE o.node_id = %(old)s AND n.node_id = %(new)s AND n.user_id = o.user_id AND n.updated_at >= o.updated_at""",
            {"old": old_id, "new": new_id})
        conn.execute(  # 옛 쪽이 더 최근이면 새 쪽을 지우고 아래에서 옛 줄을 옮긴다
            """DELETE FROM user_concept_state n USING user_concept_state o
                WHERE n.node_id = %(new)s AND o.node_id = %(old)s AND n.user_id = o.user_id AND n.updated_at < o.updated_at""",
            {"old": old_id, "new": new_id})
        conn.execute("UPDATE user_concept_state SET node_id = %s WHERE node_id = %s", (new_id, old_id))
        conn.execute("DELETE FROM concept_nodes WHERE id = %s", (old_id,))  # 카드 연결·선수 관계·이웃은 CASCADE
        moved[old_label] = new_label
    return moved


def shared_names(conn) -> dict[str, list[str]]:
    """이름·별칭 하나(term_key)가 노드 둘 이상에 걸린 것 {이름: [노드 label]}. 별칭은 더하기만 해서(사람2 노드의 탭 1
    별칭 보호) 지도에서 다른 노드로 옮긴 별칭이 옛 노드에 남을 수 있다. 지우지 않고 알려만 준다 (#263 리뷰)."""
    owners: dict[str, set[str]] = defaultdict(set)
    for label, aliases in conn.execute("SELECT label, aliases FROM concept_nodes").fetchall():
        for k in {term_key(label), *(term_key(a) for a in aliases or [])}:
            if k:
                owners[k].add(label)
    return {k: sorted(v) for k, v in sorted(owners.items()) if len(v) > 1}


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

    absorbed = absorb_renamed(conn, nodes, ids)

    node_ids = list(ids.values())
    want =sorted({c for n in nodes for c in n.get("card_ids") or []})
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

    conf = result.get("confusable_pairs")  # 검토 파일을 쓰지 않은 옛 결과 파일이면 None: 표를 건드리지 않는다
    conf_rows = []
    if conf is not None:
        conf_rows = [row for p in conf if p["a"] in ids and p["b"] in ids
                     for row in ((ids[p["a"]], ids[p["b"]], p["sim"]), (ids[p["b"]], ids[p["a"]], p["sim"]))]
        conn.execute("DELETE FROM concept_confusable")   # 지도만 쓰는 표라 통째로 지도대로
        if conf_rows:
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO concept_confusable (node_id, other_id, sim) VALUES (%s, %s, %s)",
                                conf_rows)

    linked = dict(conn.execute("SELECT label, causal_id FROM concept_nodes WHERE label = ANY(%s) AND causal_id IS NOT NULL",
                               (labels,)).fetchall())
    stale = [r[0] for r in conn.execute(
        "SELECT label FROM concept_nodes WHERE label <> ALL(%s) AND causal_id IS NULL ORDER BY id", (labels,)).fetchall()]
    return {
        "nodes": len(nodes),
        "cards": len(card_rows),
        "cards_missing": sorted(set(want) - have),
        "prereqs": len(prereq_rows),
        "confusable": None if conf is None else len(conf_rows),   # 줄 수 (한 쌍 = 두 줄)
        "causal_linked": linked,             # 지도 노드 중 탭 1 단어와 짝지어진 것 (이번에 짝지은 것 + 원래 짝지어져 있던 것)
        "causal_unclear": sorted(unclear),   # 여러 개념·여러 노드에 걸려 안 이음
        "causal_taken": sorted(taken),       # 그 개념을 이미 다른 노드가 가져서 안 이음
        "stale_nodes": stale,                # DB 에만 있고 지도에 없는 노드 (지우지 않음). 탭 1 개념 노드는 뺀 수
        "absorbed": absorbed,                # 이름을 바꾸거나 합쳐 새 노드로 기록을 옮기고 지운 옛 노드 {옛: 새}
        "shared_names": shared_names(conn),  # 이름·별칭 하나가 노드 둘 이상에 걸림 (튜터가 번호 작은 노드를 잡는다)
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
          f"선수 관계 {s['prereqs']}개, 헷갈리는 이웃 "
          f"{'(검토 파일 없는 결과라 안 건드림)' if s['confusable'] is None else str(s['confusable']) + '줄'}")
    print(f"   탭 1 단어 짝짓기 (이름만, 인과 화살표 안 씀) {len(s['causal_linked'])}개: {s['causal_linked']}")
    if s["causal_unclear"] or s["causal_taken"]:
        print(f"   안 짝지음: 애매 {s['causal_unclear']}, 다른 노드가 가짐 {s['causal_taken']}")
    if s["absorbed"]:
        print(f"   이름을 바꾸거나 합친 옛 노드 {len(s['absorbed'])}개 (학습 기록을 옮기고 지움): {s['absorbed']}")
    if s["shared_names"]:
        print(f"   ⚠ 이름·별칭이 노드 둘 이상에 걸림 {len(s['shared_names'])}개 (튜터는 번호 작은 노드를 잡음, "
              f"검토 파일이나 DB 별칭을 확인): {s['shared_names']}")
    if s["stale_nodes"]:
        print(f"   지도에 없는 DB 노드 {len(s['stale_nodes'])}개 (학습 기록 보호로 지우지 않음): {s['stale_nodes']}")


if __name__ == "__main__":
    main()
