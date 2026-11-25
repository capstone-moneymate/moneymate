"""concepts/load_map.py: 개념 지도를 009 테이블에 넣기. causal_links 는 DB 없이, load 는 실제 PostgreSQL(009 적용)에서 본다.
테스트가 쓴 것은 끝에 모두 되돌린다(rollback). DB 가 없거나 009 가 없으면 load 테스트는 건너뛴다.
"""
import uuid

import pytest

from concepts.load_map import causal_links, load
from learner import state


# --- 인과 사전 연결 (DB 없이) ---

CONCEPTS = [("rate_hold", "기준금리 동결", ["금리 동결"]), ("eps_up", "EPS 증가", []), ("eps_dn", "EPS 감소", ["EPS"])]


def test_causal_links_by_name_alias_spacing_and_parens():
    nodes = [{"label": "기준 금리 동결", "aliases": []},        # 띄어쓰기만 다름
             {"label": "금리동결(한국은행)", "aliases": []},      # 괄호 안 무시 → 별칭 '금리 동결' 과 같음: 개념 하나에 노드 둘
             {"label": "주당순이익", "aliases": ["eps"]},         # 별칭 대소문자 무시 → eps_dn 의 별칭
             {"label": "매출액", "aliases": []}]
    links, unclear = causal_links(nodes, CONCEPTS)
    assert links == {"주당순이익": "eps_dn"}
    assert unclear == ["기준 금리 동결", "금리동결(한국은행)"]   # rate_hold 가 두 노드에 걸려 애매


def test_causal_links_one_node_two_concepts_is_unclear():
    concepts = [("a", "금리", []), ("b", "이자율", ["금리"])]
    assert causal_links([{"label": "금리", "aliases": []}], concepts) == ({}, ["금리"])


# --- DB ---

@pytest.fixture
def conn():
    try:
        import psycopg

        from config import DATABASE_URL
        c = psycopg.connect(DATABASE_URL, connect_timeout=3)
        c.execute("SELECT votes FROM concept_prereq LIMIT 0")
    except Exception as e:  # DB 없음, DLL 차단, 009 미적용
        pytest.skip(f"009 가 적용된 DB 가 필요해요: {e}")
    c.rollback()
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def _card(conn):
    return conn.execute("""INSERT INTO cards (card_date, card_type, title, slides) VALUES ('2026-11-24', 1, '시험', '[]')
                           RETURNING id""").fetchone()[0]


def _map(tag, card, missing_card):
    """노드 3개: A(카드 2장, 하나는 DB 에 없음) → B (사람 keep 5표), B → C (LLM 3/4)."""
    return {
        "nodes": [
            {"id": "c001", "label": f"가{tag}", "desc": "가 설명", "aliases": [f"가별칭{tag}"], "card_ids": [card, missing_card]},
            {"id": "c002", "label": f"나{tag}", "desc": "", "aliases": [], "card_ids": [card]},
            {"id": "c003", "label": f"다{tag}", "desc": "다 설명", "aliases": [], "card_ids": []},
        ],
        "prereqs": [{"pre_id": "c001", "post_id": "c002", "votes": 5, "total": 4},
                    {"pre_id": "c002", "post_id": "c003", "votes": 3, "total": 4}],
    }


def _prereqs(conn, tag):
    return conn.execute(
        """SELECT a.label, b.label, p.votes, p.total FROM concept_prereq p
             JOIN concept_nodes a ON a.id = p.pre_id JOIN concept_nodes b ON b.id = p.post_id
            WHERE a.label LIKE %s ORDER BY 1, 2""", (f"%{tag}",)).fetchall()


def test_load_nodes_cards_prereqs_and_human_votes(conn):
    tag = uuid.uuid4().hex[:8]
    card = _card(conn)
    missing = card + 10_000_000
    s = load(conn, _map(tag, card, missing))
    assert (s["nodes"], s["cards"], s["prereqs"]) == (3, 2, 2) and s["cards_missing"] == [missing]
    assert _prereqs(conn, tag) == [(f"가{tag}", f"나{tag}", 4, 4), (f"나{tag}", f"다{tag}", 3, 4)]   # 사람 5표 → 4/4
    row = conn.execute("SELECT description, aliases FROM concept_nodes WHERE label = %s", (f"가{tag}",)).fetchone()
    assert row == ("가 설명", [f"가별칭{tag}"])
    cards = conn.execute("""SELECT n.label FROM concept_node_cards c JOIN concept_nodes n ON n.id = c.node_id
                             WHERE c.card_id = %s ORDER BY 1""", (card,)).fetchall()
    assert cards == [(f"가{tag}",), (f"나{tag}",)]


def test_load_twice_follows_the_map(conn):
    tag = uuid.uuid4().hex[:8]
    card = _card(conn)
    m = _map(tag, card, card)
    load(conn, m)
    m["prereqs"].pop()                                   # 지도에서 나 → 다 를 뺐다
    m["nodes"][0]["aliases"] = [f"새별칭{tag}"]
    m["nodes"][0]["desc"] = ""                            # 빈 설명은 원래 설명을 지우지 않는다
    m["nodes"][1]["card_ids"] = []
    s = load(conn, m)
    assert s["nodes"] == 3 and s["prereqs"] == 1
    assert _prereqs(conn, tag) == [(f"가{tag}", f"나{tag}", 4, 4)]
    assert conn.execute("SELECT count(*) FROM concept_nodes WHERE label LIKE %s", (f"%{tag}",)).fetchone()[0] == 3
    row = conn.execute("SELECT description, aliases FROM concept_nodes WHERE label = %s", (f"가{tag}",)).fetchone()
    assert row == ("가 설명", [f"가별칭{tag}", f"새별칭{tag}"])   # 별칭은 더하기만 (사람2 노드의 인과 사전 별칭 보호)
    assert conn.execute("SELECT count(*) FROM concept_node_cards WHERE card_id = %s", (card,)).fetchone()[0] == 1


def test_node_left_out_of_map_keeps_learner_state(conn):
    tag = uuid.uuid4().hex[:8]
    card = _card(conn)
    m = _map(tag, card, card)
    load(conn, m)
    user = str(uuid.uuid4())
    conn.execute("INSERT INTO users (id) VALUES (%s::uuid)", (user,))
    state.update(conn, user, f"다{tag}", True, 0.25)
    m["nodes"].pop()
    m["prereqs"].pop()
    s = load(conn, m)
    assert f"다{tag}" in s["stale_nodes"]
    assert f"다{tag}" in state.get_mastery(conn, user)        # 지우지 않아 학습 기록이 남는다


def test_causal_link_and_not_stealing(conn):
    tag = uuid.uuid4().hex[:8]
    card = _card(conn)
    conn.execute("INSERT INTO concepts (id, name, theme, aliases) VALUES (%s, %s, '테스트', %s)",
                 (f"x_{tag}", f"가 {tag}", [f"가별칭{tag}"]))
    conn.execute("INSERT INTO concepts (id, name, theme) VALUES (%s, %s, '테스트')", (f"y_{tag}", f"나{tag}"))
    # 사람2의 update_causal 이 '나' 개념 노드를 다른 이름으로 이미 만들어 둔 상황
    conn.execute("INSERT INTO concept_nodes (label, causal_id) VALUES (%s, %s)", (f"인과노드{tag}", f"y_{tag}"))
    s = load(conn, _map(tag, card, card))
    assert s["causal_linked"] == {f"가{tag}": f"x_{tag}"}     # 띄어쓰기 무시, 별칭으로도 같음
    assert s["causal_taken"] == [f"나{tag}"]                  # 이미 다른 노드가 가진 개념은 빼앗지 않는다
    assert f"인과노드{tag}" not in s["stale_nodes"]            # 인과 사전 노드는 '지도에서 빠진 노드'로 세지 않는다
    # 본 문제 답(update_causal)이 이제 개념 지도 노드의 알 확률을 고친다
    user = str(uuid.uuid4())
    conn.execute("INSERT INTO users (id) VALUES (%s::uuid)", (user,))
    before = state.get_mastery(conn, user)[f"가{tag}"]
    state.update_causal(conn, user, [f"x_{tag}"], True, 0.25)
    assert state.get_mastery(conn, user)[f"가{tag}"] > before


def test_load_confusable_both_directions_and_replace(conn):
    tag = uuid.uuid4().hex[:8]
    card = _card(conn)
    m = _map(tag, card, card)
    m["confusable_pairs"] = [{"a": f"가{tag}", "b": f"나{tag}", "sim": 0.85}]
    s = load(conn, m)
    assert s["confusable"] == 2
    rows = conn.execute(
        """SELECT a.label, b.label, round(c.sim::numeric, 2) FROM concept_confusable c
             JOIN concept_nodes a ON a.id = c.node_id JOIN concept_nodes b ON b.id = c.other_id
            WHERE a.label LIKE %s ORDER BY 1""", (f"%{tag}",)).fetchall()
    assert [(a, b, float(v)) for a, b, v in rows] == [(f"가{tag}", f"나{tag}", 0.85), (f"나{tag}", f"가{tag}", 0.85)]
    m["confusable_pairs"] = []                       # 사람이 drop 으로 바꿨다
    assert load(conn, m)["confusable"] == 0
    assert conn.execute("SELECT count(*) FROM concept_confusable").fetchone()[0] == 0
    m.pop("confusable_pairs")                        # 검토 파일 전의 옛 결과 파일: 표를 건드리지 않는다
    assert load(conn, m)["confusable"] is None


def test_renamed_node_moves_learner_records_and_is_deleted(conn):
    # #262: 지도에서 이름을 바꾸거나 합친 옛 노드(이름이 새 노드의 별칭)는 기록을 새 노드로 옮기고 지운다
    tag = uuid.uuid4().hex[:8]
    card = _card(conn)
    old, new, other = f"옛{tag}", f"새 이름{tag}", f"다른{tag}"
    load(conn, {"nodes": [{"id": "c1", "label": old, "desc": "", "aliases": [], "card_ids": [card]},
                          {"id": "c2", "label": new, "desc": "", "aliases": [], "card_ids": []},
                          {"id": "c3", "label": other, "desc": "", "aliases": [], "card_ids": []}], "prereqs": []})
    u1, u2 = str(uuid.uuid4()), str(uuid.uuid4())
    for u in (u1, u2):
        conn.execute("INSERT INTO users (id) VALUES (%s::uuid)", (u,))
    state.update(conn, u1, old, True, 0.25)                    # u1: 옛 노드에만 기록
    state.update(conn, u2, new, False, 0.25)                   # u2: 새 노드 기록이 먼저, 옛 노드 기록이 더 최근
    state.update(conn, u2, old, True, 0.25)
    old_id = conn.execute("SELECT id FROM concept_nodes WHERE label = %s", (old,)).fetchone()[0]
    conn.execute("""UPDATE user_concept_state SET updated_at = now() + interval '1 minute'
                     WHERE user_id = %s::uuid AND node_id = %s""", (u2, old_id))   # 한 트랜잭션이라 now() 가 같아서
    p_u1, p_u2 = state.get_mastery(conn, u1)[old], state.get_mastery(conn, u2)[old]
    s = load(conn, {"nodes": [{"id": "c2", "label": new, "desc": "", "aliases": [old], "card_ids": [card]},
                              {"id": "c3", "label": other, "desc": "", "aliases": [], "card_ids": []}], "prereqs": []})
    assert s["absorbed"] == {old: new} and old not in s["stale_nodes"]
    assert conn.execute("SELECT count(*) FROM concept_nodes WHERE id = %s", (old_id,)).fetchone()[0] == 0
    m1, m2 = state.get_mastery(conn, u1), state.get_mastery(conn, u2)
    assert old not in m1 and m1[new] == pytest.approx(p_u1)    # 옮겨졌다
    assert m2[new] == pytest.approx(p_u2)                      # 둘 다 있으면 더 최근 것
    assert conn.execute("SELECT count(*) FROM user_concept_state WHERE node_id = %s", (old_id,)).fetchone()[0] == 0
    s = load(conn, {"nodes": [{"id": "c2", "label": new, "desc": "", "aliases": [old], "card_ids": [card]}],
                    "prereqs": []})
    assert s["absorbed"] == {} and other in s["stale_nodes"]    # 별칭이 아닌 노드는 지금처럼 지우지 않는다
