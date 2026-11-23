"""learner/state.py: 실제 PostgreSQL(009 적용)에서 돈다. 테스트가 쓴 것은 끝에 모두 되돌린다(rollback).
DB 가 없거나 009 가 없으면 건너뛴다. Windows 에서 psycopg DLL 이 막히면 Docker 로 돌린다 (docs/modules/learner_state.md).
"""
import uuid

import pytest

from learner import bkt, state


@pytest.fixture
def conn():
    try:
        import psycopg

        from config import DATABASE_URL
        c = psycopg.connect(DATABASE_URL, connect_timeout=3)
        c.execute("SELECT 1 FROM user_concept_state LIMIT 0")
    except Exception as e:  # DB 없음, DLL 차단, 009 미적용
        pytest.skip(f"009 가 적용된 DB 가 필요해요: {e}")
    c.rollback()
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def _node(conn, label, causal_id=None):
    return conn.execute("INSERT INTO concept_nodes (label, causal_id) VALUES (%s, %s) RETURNING id",
                        (label, causal_id)).fetchone()[0]


def _names():
    tag = uuid.uuid4().hex[:8]
    return str(uuid.uuid4()), f"테스트 EPS {tag}", f"테스트 순이익 {tag}", f"test_concept_{tag}"


def test_new_user_starts_at_init(conn):
    user, eps, profit, _ = _names()
    _node(conn, eps), _node(conn, profit)
    m = state.get_mastery(conn, user)
    assert m[eps] == m[profit] == pytest.approx(bkt.DEFAULT.p_init)


def test_update_follows_bkt_and_is_per_concept(conn):
    user, eps, profit, _ = _names()
    _node(conn, eps), _node(conn, profit)
    assert state.update(conn, user, eps, True, 0.25) == pytest.approx(0.6461, abs=1e-4)   # 손계산 (test_bkt)
    assert state.update(conn, user, eps, True, 0.25) == pytest.approx(0.8811, abs=1e-4)   # 0.30 → 0.65 → 0.88
    assert state.update(conn, user, profit, False, 0.25) == pytest.approx(0.1486, abs=1e-4)
    m = state.get_mastery(conn, user)
    assert m[eps] == pytest.approx(0.8811, abs=1e-4) and m[profit] == pytest.approx(0.1486, abs=1e-4)
    # 다른 사용자는 그대로 처음 값
    assert state.get_mastery(conn, str(uuid.uuid4()))[eps] == pytest.approx(0.3)


def test_unknown_concept_raises(conn):
    with pytest.raises(state.UnknownConcept):
        state.update(conn, str(uuid.uuid4()), "없는 개념 " + uuid.uuid4().hex, True, 0.25)


def test_update_causal_creates_node_once(conn):
    user, _, _, cid = _names()
    conn.execute("INSERT INTO concepts (id, name, theme, aliases) VALUES (%s, %s, '테스트', %s)",
                 (cid, f"이름 {cid}", ["다른 말"]))
    out = state.update_causal(conn, user, [cid, cid, "", "없는_id_" + uuid.uuid4().hex], True, 0.5)
    assert list(out) == [cid]                                   # 중복·빈 값·사전에 없는 id 는 빠진다
    assert out[cid] == pytest.approx(0.4919, abs=1e-4)          # O/X 손계산
    state.update_causal(conn, user, [cid], True, 0.5)
    rows = conn.execute("SELECT label, aliases FROM concept_nodes WHERE causal_id = %s", (cid,)).fetchall()
    assert rows == [(f"이름 {cid}", ["다른 말"])]                 # 노드는 하나만
    assert state.get_mastery(conn, user)[f"이름 {cid}"] == pytest.approx(0.6719, abs=1e-4)


def test_update_causal_links_same_label_node(conn):
    user, eps, _, cid = _names()
    node_id = _node(conn, eps)                                  # 개념 단계 용어로 먼저 생긴 노드
    conn.execute("INSERT INTO concepts (id, name, theme) VALUES (%s, %s, '테스트')", (cid, eps))
    state.update(conn, user, eps, True, 0.25)                   # 개념 퀴즈로 0.65
    out = state.update_causal(conn, user, [cid], True, 0.25)    # 본 문제도 같은 노드에 쌓인다 → 0.88
    assert out[cid] == pytest.approx(0.8811, abs=1e-4)
    assert conn.execute("SELECT id FROM concept_nodes WHERE causal_id = %s", (cid,)).fetchall() == [(node_id,)]
