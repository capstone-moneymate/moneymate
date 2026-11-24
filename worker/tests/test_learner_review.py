"""learner/review.py: 복습 문제 고르기·보관·채점. 종류 고르기와 보기 섞기는 DB 없이, 나머지는 실제 PostgreSQL(011·012 적용)에서
돈다. 테스트가 쓴 것은 끝에 모두 되돌린다(rollback). DB 가 없거나 011·012 가 없으면 그 테스트는 건너뛴다. LLM 은 부르지 않는다.
"""
import random
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from learner import review, state
from tutor import quiz as qz

T0 = datetime(2026, 11, 24, 9, 0, tzinfo=timezone.utc)   # KST 11/24 18:00

CHOICE = {"question": "EPS 의 뜻은?", "options": ["주당순이익", "주가수익비율", "자기자본"], "answer_index": 0,
          "explanation": "순이익을 주식 수로 나눈 값"}


def test_kind_rotates_by_issued_count():
    assert [review.pick_kind(n) for n in range(5)] == ["용어 뜻", "틀린 설명", "O/X", "용어 뜻", "틀린 설명"]


def test_kind_rotation_includes_pair_only_with_a_neighbour():
    assert [review.pick_kind(n, True) for n in range(5)] == ["용어 뜻", "헷갈리는 쌍", "틀린 설명", "O/X", "용어 뜻"]
    assert "헷갈리는 쌍" not in [review.pick_kind(n, False) for n in range(12)]


def test_pair_desc_names_both_concepts():
    assert review.pair_desc("영업이익", "본업 이익", "당기순이익", "최종 이익") == "영업이익: 본업 이익\n당기순이익: 최종 이익"
    assert review.pair_desc("영업이익", "본업 이익", "당기순이익", "") == "영업이익: 본업 이익"   # 설명 없는 쪽은 뺀다
    assert review.pair_desc("영업이익", "", "당기순이익", "") == ""


def test_shuffle_moves_key_with_its_option():
    content = {"question": "q", "options": ["정답", "오답1", "오답2"]}
    seen = set()
    for seed in range(20):
        out, key = review.shuffle_options(content, 0, random.Random(seed))
        assert sorted(out["options"]) == sorted(content["options"]) and out["question"] == "q"
        assert out["options"][key] == "정답"       # 어디로 가든 정답 번호가 따라간다
        seen.add(key)
    assert seen == {0, 1, 2}                       # 정답이 한 자리에만 있지 않다
    assert content["options"] == ["정답", "오답1", "오답2"]   # 원본은 그대로


@pytest.fixture
def conn():
    try:
        import psycopg

        from config import DATABASE_URL
        c = psycopg.connect(DATABASE_URL, connect_timeout=3)
        c.execute("SELECT answer_key FROM concept_quizzes LIMIT 0")
        c.execute("SELECT sim FROM concept_confusable LIMIT 0")
    except Exception as e:  # DB 없음, DLL 차단, 011·012 미적용
        pytest.skip(f"011·012 가 적용된 DB 가 필요해요: {e}")
    c.rollback()
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def _due_concept(conn, days_ago=10):
    """days_ago 일 전에 한 번 맞힌 개념 (첫 Good 은 2일 뒤가 복습일이라 T0 에는 복습일이 지났다)."""
    user, label = str(uuid.uuid4()), f"테스트 개념 {uuid.uuid4().hex[:8]}"
    node = conn.execute("INSERT INTO concept_nodes (label, description) VALUES (%s, %s) RETURNING id",
                        (label, "테스트용 설명")).fetchone()[0]
    state.update(conn, user, label, True, 0.25, now=T0 - timedelta(days=days_ago))
    return user, label, node


def _quiz(label, kind="용어 뜻"):
    return qz.to_quiz(kind, label, CHOICE)


def test_prepare_gives_material_for_a_due_concept(conn):
    user, label, node = _due_concept(conn)
    assert review.prepare(conn, user, node, T0) == {"concept": label, "desc": "테스트용 설명", "kind": "용어 뜻",
                                                    "pair": None}


def test_prepare_rejects_concept_not_in_todays_list(conn):
    user, _, node = _due_concept(conn, days_ago=0)        # 방금 풀어서 복습일이 2일 뒤
    with pytest.raises(review.NotDue):
        review.prepare(conn, user, node, T0)
    with pytest.raises(review.NotDue):                     # 풀어 본 적 없는 사용자
        review.prepare(conn, str(uuid.uuid4()), node, T0)


def test_description_falls_back_to_concept_step_term(conn):
    user, label = str(uuid.uuid4()), f"테스트 용어 {uuid.uuid4().hex[:8]}"
    node = conn.execute("INSERT INTO concept_nodes (label, aliases) VALUES (%s, %s) RETURNING id",
                        (label, [label + " 별칭"])).fetchone()[0]
    card = conn.execute("""INSERT INTO cards (card_date, card_type, status, title, slides)
                           VALUES ('2026-11-20', 1, 'published', '테스트 카드', '[]') RETURNING id""").fetchone()[0]
    conn.execute("INSERT INTO steps (card_id, step_no, kind, content) VALUES (%s, 1, 'concept', %s::jsonb)",
                 (card, '{"terms": [{"term": "%s 별칭", "desc": "카드에서 풀이한 뜻"}]}' % label))
    state.update(conn, user, label, True, 0.25, now=T0 - timedelta(days=10))
    assert review.prepare(conn, user, node, T0)["desc"] == "카드에서 풀이한 뜻"   # 별칭으로도 찾는다


def test_save_keeps_key_on_server_and_reuses_unanswered_quiz(conn):
    user, label, node = _due_concept(conn)
    out = review.save(conn, user, node, _quiz(label), random.Random(1))
    assert set(out) == {"quiz_id", "node_id", "concept", "kind", "content", "guess_p"}   # 정답·해설은 안 나간다
    assert out["concept"] == label and out["guess_p"] == 0.3333
    assert sorted(out["content"]["options"]) == sorted(CHOICE["options"])
    key, = conn.execute("SELECT answer_key FROM concept_quizzes WHERE id = %s", (out["quiz_id"],)).fetchone()
    assert out["content"]["options"][key] == "주당순이익"            # 섞은 뒤에도 보관한 정답이 맞는 보기를 가리킨다
    # 아직 안 풀었으면 다시 들어와도 같은 문제 (LLM 을 다시 부르지 않는다)
    assert review.prepare(conn, user, node, T0) == {"pending": out}


def test_answer_updates_state_logs_and_closes_quiz(conn):
    user, label, node = _due_concept(conn)
    out = review.save(conn, user, node, _quiz(label), random.Random(1))
    key, = conn.execute("SELECT answer_key FROM concept_quizzes WHERE id = %s", (out["quiz_id"],)).fetchone()
    before = state.get_mastery(conn, user)[label]

    got = review.answer(conn, user, out["quiz_id"], key, 2, response_ms=4000, answer_changes=0, now=T0)

    assert got["correct"] is True and got["key"] == key and got["explanation"] == CHOICE["explanation"]
    assert got["concept"] == label and got["p_know"] > before
    assert got["due_at"] > T0 + timedelta(days=2)             # 두 번째 Good 은 간격이 더 벌어진다
    row = conn.execute("""SELECT source, quiz_kind, is_correct, confidence, response_ms, answer_changes, answer, card_id
                            FROM concept_answers WHERE user_id = %s::uuid AND node_id = %s""", (user, node)).fetchone()
    assert row == ("review", "용어 뜻", True, 2, 4000, 0, key, None)
    # 복습했으니 오늘 목록에서 빠지고 오늘 복습한 수가 1 늘어난다
    due = state.due_reviews(conn, user, T0)
    assert due["done_today"] == 1 and due["items"] == []
    with pytest.raises(review.AlreadyAnswered):
        review.answer(conn, user, out["quiz_id"], key, 2, now=T0)


def test_wrong_sure_answer_goes_to_front_and_next_kind_changes(conn):
    user, label, node = _due_concept(conn)
    out = review.save(conn, user, node, _quiz(label), random.Random(1))
    key, = conn.execute("SELECT answer_key FROM concept_quizzes WHERE id = %s", (out["quiz_id"],)).fetchone()

    got = review.answer(conn, user, out["quiz_id"], (key + 1) % 3, "확실해요", now=T0)

    assert got["correct"] is False and got["key"] == key
    tomorrow = T0 + timedelta(days=1)                         # 틀리면(Again) 1일 뒤가 복습일
    due = state.due_reviews(conn, user, tomorrow)
    assert [(i["node_id"], i["reason"]) for i in due["items"]] == [(node, "sure_wrong")]
    assert review.prepare(conn, user, node, tomorrow)["kind"] == "틀린 설명"   # 같은 개념, 다른 종류


def test_other_users_quiz_is_not_found(conn):
    user, label, node = _due_concept(conn)
    out = review.save(conn, user, node, _quiz(label), random.Random(1))
    with pytest.raises(review.QuizNotFound):
        review.answer(conn, str(uuid.uuid4()), out["quiz_id"], 0, now=T0)
    with pytest.raises(review.QuizNotFound):
        review.answer(conn, user, -1, 0, now=T0)


# ---------- 헷갈리는 쌍 (concept_confusable, 012) ----------

def _neighbour(conn, node, sim, desc="이웃 설명"):
    label = f"테스트 이웃 {uuid.uuid4().hex[:8]}"
    other = conn.execute("INSERT INTO concept_nodes (label, description) VALUES (%s, %s) RETURNING id",
                         (label, desc)).fetchone()[0]
    conn.execute("INSERT INTO concept_confusable (node_id, other_id, sim) VALUES (%s, %s, %s)", (node, other, sim))
    return label


def _issue(conn, user, label, node, kind, now):
    """종류가 kind 인 문제를 내고 맞힌다 (다음 문제를 낼 수 있게)."""
    options = ["a", "b"] if kind == "헷갈리는 쌍" else ["a", "b", "c"]
    quiz = qz.Quiz(kind, label, {"question": "q", "options": options}, 0, "해설", 1 / len(options))
    out = review.save(conn, user, node, quiz, random.Random(1))
    key, = conn.execute("SELECT answer_key FROM concept_quizzes WHERE id = %s", (out["quiz_id"],)).fetchone()
    review.answer(conn, user, out["quiz_id"], key, now=now)


def test_neighbours_are_ordered_by_similarity_and_one_way(conn):
    user, label, node = _due_concept(conn)
    low = _neighbour(conn, node, 0.71)
    high = _neighbour(conn, node, 0.86, desc=None)
    assert review.neighbours(conn, node) == [(high, ""), (low, "이웃 설명")]
    # 한 줄은 한 방향: 이웃 쪽에서 보면 이 개념은 이웃이 아니다 (반대 줄을 넣지 않았다)
    other_id, = conn.execute("SELECT id FROM concept_nodes WHERE label = %s", (high,)).fetchone()
    assert review.neighbours(conn, other_id) == []


def test_pair_quiz_comes_second_and_rotates_through_neighbours(conn):
    user, label, node = _due_concept(conn)
    low = _neighbour(conn, node, 0.71, desc="낮은 이웃 설명")
    high = _neighbour(conn, node, 0.86, desc="높은 이웃 설명")

    seen, now = [], T0
    for _ in range(5):                                                         # 뜻, 쌍, 틀린 설명, O/X, 뜻 을 차례로 낸다
        plan = review.prepare(conn, user, node, now)
        seen.append((plan["kind"], plan["pair"]))
        _issue(conn, user, label, node, plan["kind"], now)
        now += timedelta(days=1)                                               # 다음 날, 복습일이 된 것으로 둔다
        conn.execute("UPDATE user_concept_state SET due_at = %s WHERE user_id = %s::uuid AND node_id = %s",
                     (now - timedelta(hours=1), user, node))
    plan = review.prepare(conn, user, node, now)                               # 여섯 번째 = 두 번째 쌍 문제

    assert seen == [("용어 뜻", None), ("헷갈리는 쌍", [label, high]), ("틀린 설명", None), ("O/X", None),
                    ("용어 뜻", None)]                                          # 이웃이 있어도 첫 문제는 뜻
    assert plan["kind"] == "헷갈리는 쌍" and plan["pair"] == [label, low]      # 유사도 높은 이웃 다음은 그다음 이웃
    assert plan["desc"] == f"{label}: 테스트용 설명\n{low}: 낮은 이웃 설명"


def test_pair_quiz_is_saved_shuffled_and_graded(conn):
    user, label, node = _due_concept(conn)
    other = _neighbour(conn, node, 0.8)
    data = {"question": "본업에서 번 이익은?", "options": [label, other], "answer_index": 1, "explanation": "해설"}
    quiz = qz.to_quiz("헷갈리는 쌍", label, data, pair=[label, other])

    out = review.save(conn, user, node, quiz, random.Random(3))

    assert out["kind"] == "헷갈리는 쌍" and out["guess_p"] == 0.5
    assert sorted(out["content"]["options"]) == sorted([label, other])
    key, = conn.execute("SELECT answer_key FROM concept_quizzes WHERE id = %s", (out["quiz_id"],)).fetchone()
    assert out["content"]["options"][key] == other                              # 정답이 이웃이어도 번호가 따라간다
    got = review.answer(conn, user, out["quiz_id"], key, 2, now=T0)
    assert got["correct"] is True and got["concept"] == label                   # 알 확률은 복습하던 개념에 반영
    kind, guess = conn.execute(
        "SELECT quiz_kind, guess_p FROM concept_answers WHERE user_id = %s::uuid AND node_id = %s", (user, node)).fetchone()
    assert (kind, guess) == ("헷갈리는 쌍", 0.5)
