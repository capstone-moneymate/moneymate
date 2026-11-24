"""learner/state.py: 실제 PostgreSQL(009 적용)에서 돈다. 테스트가 쓴 것은 끝에 모두 되돌린다(rollback).
DB 가 없거나 009 가 없으면 건너뛴다. Windows 에서 psycopg DLL 이 막히면 Docker 로 돌린다 (docs/modules/learner_state.md).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from learner import bkt, state

T0 = datetime(2026, 11, 24, 9, 0, tzinfo=timezone.utc)   # KST 11/24 18:00


@pytest.fixture
def conn():
    try:
        import psycopg

        from config import DATABASE_URL
        c = psycopg.connect(DATABASE_URL, connect_timeout=3)
        c.execute("SELECT sure_wrong_at FROM user_concept_state LIMIT 0")
    except Exception as e:  # DB 없음, DLL 차단, 009·010 미적용
        pytest.skip(f"009·010 이 적용된 DB 가 필요해요: {e}")
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


# ---------- 복습 일정 (FSRS, 계획 2-4) ----------

def _row(conn, user, label):
    return conn.execute(
        """SELECT s.stability, s.difficulty, s.fsrs_state, s.last_review_at, s.due_at, s.sure_wrong_at
             FROM user_concept_state s JOIN concept_nodes n ON n.id = s.node_id
            WHERE s.user_id = %s::uuid AND n.label = %s""", (user, label)).fetchone()


def test_answer_also_schedules_review(conn):
    user, eps, profit, _ = _names()
    _node(conn, eps), _node(conn, profit)
    state.update(conn, user, eps, True, 0.25, 2, now=T0)       # 맞힘 + 확실해요 → Good
    state.update(conn, user, profit, True, 0.25, 1, now=T0)    # 맞힘 + 헷갈려요 → Hard
    stability, difficulty, fsrs_state, last_review, due, sure_wrong = _row(conn, user, eps)
    assert stability == pytest.approx(2.3065, abs=1e-4)        # 손계산 (test_schedule): Good 의 처음 안정도
    assert difficulty == pytest.approx(2.118, abs=1e-3)
    assert (fsrs_state, last_review, due, sure_wrong) == (2, T0, T0 + timedelta(days=2), None)
    hard = _row(conn, user, profit)
    assert hard[0] == pytest.approx(1.2931, abs=1e-4) and hard[4] == T0 + timedelta(days=1)


def test_sure_but_wrong_is_marked_until_next_correct(conn):
    user, eps, profit, _ = _names()
    _node(conn, eps), _node(conn, profit)
    state.update(conn, user, eps, False, 0.25, 2, now=T0)      # 확실해요 + 틀림
    state.update(conn, user, profit, False, 0.25, 1, now=T0)   # 헷갈려요 + 틀림은 표시하지 않는다
    assert _row(conn, user, eps)[5] == T0
    assert _row(conn, user, eps)[4] == T0 + timedelta(days=1)  # Again → 다음 날
    assert _row(conn, user, profit)[5] is None
    state.update(conn, user, eps, False, 0.25, 1, now=T0 + timedelta(days=1))   # 또 틀려도(헷갈려요) 표시는 남는다
    assert _row(conn, user, eps)[5] == T0
    state.update(conn, user, eps, True, 0.25, 1, now=T0 + timedelta(days=2))    # 맞히면 지운다
    assert _row(conn, user, eps)[5] is None


def test_fast_sure_correct_without_changes_is_easy(conn):
    user, eps, profit, other = _names()
    eps_id = _node(conn, eps)
    _node(conn, profit), _node(conn, other)
    conn.execute("INSERT INTO users (id) VALUES (%s::uuid)", (user,))
    for ms in (4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000):   # 같은 종류를 맞혔던 지난 8번
        conn.execute(
            """INSERT INTO concept_answers (user_id, node_id, source, quiz_kind, is_correct, response_ms)
               VALUES (%s::uuid, %s, 'tutor', 'term_meaning', true, %s)""", (user, eps_id, ms))
    kw = {"kind": "term_meaning", "now": T0}
    state.update(conn, user, eps, True, 0.33, 2, response_ms=4500, answer_changes=0, **kw)      # 빠른 쪽 1/4 → Easy
    state.update(conn, user, profit, True, 0.33, 2, response_ms=4500, answer_changes=1, **kw)   # 답을 바꿈 → Good
    state.update(conn, user, other, True, 0.33, 2, response_ms=9000, answer_changes=0, **kw)    # 느림 → Good
    assert _row(conn, user, eps)[0] == pytest.approx(8.2956, abs=1e-4)
    assert _row(conn, user, eps)[4] == T0 + timedelta(days=8)
    assert _row(conn, user, profit)[0] == pytest.approx(2.3065, abs=1e-4)
    assert _row(conn, user, other)[0] == pytest.approx(2.3065, abs=1e-4)


def test_due_reviews_order_and_daily_limit(conn):
    user = str(uuid.uuid4())
    tag = uuid.uuid4().hex[:6]
    labels = [f"복습{i} {tag}" for i in range(8)]
    ids = [_node(conn, x) for x in labels]
    state.update(conn, user, labels[0], True, 0.25, 2, now=T0)                       # Good  → 2일 뒤
    state.update(conn, user, labels[1], True, 0.25, 1, now=T0)                       # Hard  → 1일 뒤
    state.update(conn, user, labels[2], False, 0.25, 1, now=T0)                      # Again → 1일 뒤 (헷갈려요)
    state.update(conn, user, labels[3], False, 0.25, 2, now=T0)                      # 확실해요 + 틀림
    state.update(conn, user, labels[4], False, 0.25, 2, now=T0 + timedelta(hours=1))  # 확실해요 + 틀림 (더 최근)
    state.update(conn, user, labels[5], True, 0.25, 2, now=T0 - timedelta(days=1))   # Good, 하루 먼저 → 1일 뒤
    state.update(conn, user, labels[6], True, 0.25, 1, now=T0 - timedelta(days=1))   # Hard, 하루 먼저
    # labels[7] 은 안 풀었다 → 복습 대상이 아니다

    assert state.due_reviews(conn, user, now=T0)["due_total"] == 1                    # 오늘은 labels[6] 만 (어제 Hard)

    now = T0 + timedelta(days=3)
    out = state.due_reviews(conn, user, now=now)
    assert (out["limit"], out["done_today"], out["due_total"]) == (5, 0, 7)
    got = [i["concept"] for i in out["items"]]
    # ① 확실해요 + 틀림: 더 최근 것부터 ② 기억 확률 낮은 순: Again(안정도 0.21) < Hard 4일 < Hard 3일 ...
    assert got == [labels[4], labels[3], labels[2], labels[6], labels[1]]
    assert [i["reason"] for i in out["items"]] == ["sure_wrong", "sure_wrong", "due", "due", "due"]
    r = [i["retrievability"] for i in out["items"][2:]]
    assert r == sorted(r) and all(0 < x < 0.9 for x in r)

    # 오늘 복습한 개념 수만큼 상한에서 뺀다 (같은 개념을 두 번 풀어도 한 개)
    for _ in range(2):
        conn.execute(
            """INSERT INTO concept_answers (user_id, node_id, source, quiz_kind, is_correct, created_at)
               VALUES (%s::uuid, %s, 'review', 'ox', true, %s)""", (user, ids[7], now))
    out = state.due_reviews(conn, user, now=now)
    assert out["done_today"] == 1 and len(out["items"]) == 4


def test_due_is_compared_by_kst_date(conn):
    user, eps, _, _ = _names()
    _node(conn, eps)
    state.update(conn, user, eps, True, 0.25, 2, now=T0)       # 복습일 = 11/26 18:00 KST
    early = datetime(2026, 11, 25, 15, 30, tzinfo=timezone.utc)   # 11/26 00:30 KST: 시각은 아직이지만 날짜는 됐다
    assert state.due_reviews(conn, user, now=early)["due_total"] == 1
    before = datetime(2026, 11, 25, 14, 30, tzinfo=timezone.utc)  # 11/25 23:30 KST
    assert state.due_reviews(conn, user, now=before)["due_total"] == 0


# ---------- 확신 보정 (계획 2-5) ----------

def _quiz_answer(conn, user, node_id, correct, confidence, when):
    conn.execute(
        """INSERT INTO concept_answers (user_id, node_id, source, quiz_kind, is_correct, confidence, created_at)
           VALUES (%s::uuid, %s, 'tutor', 'ox', %s, %s, %s)""", (user, node_id, correct, confidence, when))


def test_confidence_table_counts_both_answer_tables(conn):
    user, eps, _, _ = _names()
    node_id = _node(conn, eps)
    conn.execute("INSERT INTO users (id) VALUES (%s::uuid)", (user,))
    for correct, confidence, n in ((True, 2, 3), (False, 2, 1), (True, 1, 2), (False, 1, 4)):
        for _ in range(n):
            _quiz_answer(conn, user, node_id, correct, confidence, T0)
    _quiz_answer(conn, user, node_id, True, None, T0)                    # 확신 없이 낸 답은 세지 않는다
    step = conn.execute("SELECT id, card_id FROM steps WHERE kind = 'quiz' LIMIT 1").fetchone()
    extra = 0
    if step:                                                             # 본 문제 답도 같은 표에 들어간다
        conn.execute(
            """INSERT INTO user_answers (user_id, card_id, step_id, answer, is_correct, graded_by, confidence, created_at)
               VALUES (%s::uuid, %s, %s, '{}'::jsonb, false, 'code', 2, %s)""", (user, step[1], step[0], T0))
        extra = 1
    t = state.confidence_table(conn, user)
    assert (t.sure_right, t.sure_wrong, t.unsure_right, t.unsure_wrong) == (3, 1 + extra, 2, 4)
    assert state.confidence_table(conn, str(uuid.uuid4())).total == 0     # 다른 사용자는 0


def test_calibration_report_splits_recent_and_earlier(conn):
    user, eps, profit, _ = _names()
    eps_id = _node(conn, eps)
    _node(conn, profit)
    now = T0 + timedelta(days=40)
    conn.execute("INSERT INTO users (id) VALUES (%s::uuid)", (user,))
    for _ in range(6):                                                   # 40일 전: 확실해요인데 틀림 6
        _quiz_answer(conn, user, eps_id, False, 2, T0)
    for _ in range(4):                                                   # 40일 전: 확실해요 + 맞힘 4
        _quiz_answer(conn, user, eps_id, True, 2, T0)
    for _ in range(8):                                                   # 5일 전: 확실해요 + 맞힘 8
        _quiz_answer(conn, user, eps_id, True, 2, now - timedelta(days=5))
    for _ in range(2):                                                   # 5일 전: 헷갈려요 + 틀림 2
        _quiz_answer(conn, user, eps_id, False, 1, now - timedelta(days=5))
    state.update(conn, user, profit, False, 0.25, 2, now=now - timedelta(days=1))   # 확실해요인데 틀린 개념

    r = state.calibration_report(conn, user, now=now)
    assert r["recent_days"] == 30
    assert (r["all"]["total"], r["earlier"]["total"], r["recent"]["total"]) == (20, 10, 10)
    assert r["all"]["enough"] is True and r["recent"]["enough"] is False
    assert r["earlier"]["bias"] == pytest.approx(0.6)        # 확실해요 10/10 - 정답 4/10: 과신
    assert r["recent"]["bias"] == pytest.approx(0.0)         # 확실해요 8/10 - 정답 8/10: 과신이 줄었다
    assert r["earlier"]["illusion"] == 1.0 and r["recent"]["illusion"] == 0.0
    assert r["sure_wrong_concepts"] == [profit]
