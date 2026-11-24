"""튜터 + 진짜 BKT (#230): DbMastery, ConceptMap.from_db, card_targets. 실제 PostgreSQL(009·011·012 적용)에서 돈다.
테스트가 쓴 것은 끝에 모두 되돌린다(rollback). DB 가 없거나 표가 없으면 건너뛴다. LLM 은 부르지 않는다.
"""
import json
import uuid

import pytest

from learner import state
from tutor import agent as ag
from tutor.mastery import DbMastery
from tutor.quiz import Quiz


@pytest.fixture
def conn():
    try:
        import psycopg

        from config import DATABASE_URL
        c = psycopg.connect(DATABASE_URL, connect_timeout=3)
        c.execute("SELECT attempt_no FROM concept_answers LIMIT 0")
        c.execute("SELECT sim FROM concept_confusable LIMIT 0")
    except Exception as e:  # DB 없음, DLL 차단, 009·012 미적용
        pytest.skip(f"009·012 가 적용된 DB 가 필요해요: {e}")
    c.rollback()
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def _setup(conn):
    """노드 3개(가 → 나, 가 ↔ 다 헷갈림), 카드 하나(개념 단계 용어: '나', '가 (괄호)', 지도에 없는 말), 사용자 하나."""
    tag = uuid.uuid4().hex[:8]
    ids = {}
    for name, desc in (("가", "가 설명"), ("나", "나 설명"), ("다", "")):
        ids[name] = conn.execute("INSERT INTO concept_nodes (label, description, aliases) VALUES (%s, %s, %s) RETURNING id",
                                 (f"{name}{tag}", desc or None, [f"{name}별칭{tag}"])).fetchone()[0]
    conn.execute("INSERT INTO concept_prereq (pre_id, post_id, votes, total) VALUES (%s, %s, 4, 4)", (ids["가"], ids["나"]))
    conn.execute("INSERT INTO concept_confusable (node_id, other_id, sim) VALUES (%s, %s, 0.8), (%s, %s, 0.8)",
                 (ids["가"], ids["다"], ids["다"], ids["가"]))
    card = conn.execute("""INSERT INTO cards (card_date, card_type, title, slides) VALUES ('2026-11-24', 1, '시험', '[]')
                           RETURNING id""").fetchone()[0]
    terms = [{"term": f"나{tag}", "desc": ""}, {"term": f"가 {tag}(괄호)", "desc": ""}, {"term": "지도에 없음", "desc": ""}]
    conn.execute("""INSERT INTO steps (card_id, step_no, kind, content) VALUES (%s, 0, 'concept', %s::jsonb)""",
                 (card, json.dumps({"terms": terms}, ensure_ascii=False)))
    user = str(uuid.uuid4())
    conn.execute("INSERT INTO users (id) VALUES (%s::uuid)", (user,))
    return tag, card, user


def _quiz(tag, name="가"):
    return Quiz("용어 뜻", f"{name}{tag}", {"question": "?", "options": ["a", "b", "c", "d"]}, 0, "설명", 0.25)


def test_map_and_targets_from_db(conn):
    tag, card, _ = _setup(conn)
    m = ag.ConceptMap.from_db(conn)
    assert (f"가{tag}", f"나{tag}", 4) in m.edges and m.desc[f"가{tag}"] == "가 설명" and m.desc[f"다{tag}"] == ""
    assert m.confusable[f"가{tag}"] == [f"다{tag}"] and m.confusable[f"다{tag}"] == [f"가{tag}"]
    # 개념 단계 용어 순서, 괄호·띄어쓰기 무시, 지도에 없는 용어는 건너뜀
    assert ag.card_targets(conn, card) == [f"나{tag}", f"가{tag}"]


def test_answer_updates_bkt_and_records(conn):
    tag, card, user = _setup(conn)
    mm = DbMastery(conn, card, commit=False)
    before = mm.get_mastery(user)[f"가{tag}"]
    p = mm.answer(user, _quiz(tag), 0, True, "확신해요", response_ms=4200, answer_changes=1)
    assert p > before and state.get_mastery(conn, user)[f"가{tag}"] == pytest.approx(p)
    row = conn.execute(
        """SELECT source, card_id, attempt_no, quiz_kind, guess_p, quiz->>'question', answer, is_correct, confidence,
                  response_ms, answer_changes FROM concept_answers WHERE user_id = %s::uuid""", (user,)).fetchone()
    assert row == ("tutor", card, 1, "용어 뜻", pytest.approx(0.25), "?", 0, True, 2, 4200, 1)


def test_attempt_is_max_plus_one_and_fixed_for_session(conn):
    tag, card, user = _setup(conn)
    step = conn.execute("INSERT INTO steps (card_id, step_no, kind, content) VALUES (%s, 1, 'quiz', '{}') RETURNING id",
                        (card,)).fetchone()[0]
    conn.execute("""INSERT INTO user_answers (user_id, card_id, step_id, answer, attempt_no)
                    VALUES (%s::uuid, %s, %s, '0', 1), (%s::uuid, %s, %s, '0', 2)""", (user, card, step, user, card, step))
    mm = DbMastery(conn, card, commit=False)
    mm.answer(user, _quiz(tag), 1, False, "애매해요")
    # 세션 중에 본 문제 답이 생겨도(다른 화면) 이 세션의 개념 단계 답은 같은 시도 번호
    conn.execute("INSERT INTO user_answers (user_id, card_id, step_id, answer, attempt_no) VALUES (%s::uuid, %s, %s, '0', 3)",
                 (user, card, step))
    mm.answer(user, _quiz(tag, "나"), 0, True, None)
    rows = conn.execute("SELECT attempt_no, confidence FROM concept_answers WHERE user_id = %s::uuid ORDER BY id",
                        (user,)).fetchall()
    assert rows == [(3, 1), (3, None)]


def test_no_card_means_no_attempt(conn):
    tag, _, user = _setup(conn)
    DbMastery(conn, None, commit=False).answer(user, _quiz(tag), 0, True, 2)
    assert conn.execute("SELECT card_id, attempt_no FROM concept_answers WHERE user_id = %s::uuid",
                        (user,)).fetchone() == (None, None)


def test_tutor_answer_goes_through_db_mastery(conn, monkeypatch):
    # 튜터 answer() 가 DbMastery 로 기록하고, 모델에게 새 알 확률을 넘긴다 (모델 호출은 가짜: 바로 go_main)
    tag, card, user = _setup(conn)
    s = ag.Session(user, ag.ConceptMap.from_db(conn), [f"가{tag}"], DbMastery(conn, card, commit=False), card="시험",
                   card_id=card)
    s.status, s.pending = "waiting", ("t1", _quiz(tag))
    s.log.append({"tool": "ask_quiz", "input": {}, "reason": "r"})
    monkeypatch.setattr(ag, "_advance", lambda s: s)
    s = ag.answer(s, 0, "확신해요", response_ms=3000)
    sent = json.loads(s.messages[-1]["content"][0]["content"])
    assert sent["correct"] is True and sent["p_know_now"] == round(state.get_mastery(conn, user)[f"가{tag}"], 2)
    assert conn.execute("SELECT count(*) FROM concept_answers WHERE user_id = %s::uuid AND source = 'tutor'",
                        (user,)).fetchone()[0] == 1
