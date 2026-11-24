"""복습 문제 내기와 채점 (사람2, 계획 2-4·2-7). 오늘 복습할 개념(state.due_reviews)마다 새 문제를 하나 낸다.

- 문제는 사람1의 worker/tutor/quiz.py 가 만든다 (문장은 LLM, 모양 검사·찍어서 맞힐 확률은 코드).
  여기서는 어떤 종류를 낼지 고르고, 정답을 concept_quizzes(011)에 보관하고, 답이 오면 채점해서
  알 확률(BKT)과 복습 일정(FSRS)을 고친 뒤 concept_answers 에 남긴다.
- 종류는 화면 A(보기 고르기) 중 개념 하나로 낼 수 있는 세 가지를 돌아가며 낸다 (KINDS). 같은 개념을 복습할 때마다
  종류가 바뀌고 문장도 새로 만들어져서 문제를 외워서 맞히기 어렵다.
- 오늘 복습 목록에 있는 개념만 낸다. 목록이 하루 상한과 복습일을 지키므로 여기서 LLM 호출 수도 같이 묶인다.
- 정답 보기 위치는 코드가 섞는다 (LLM 이 정답을 특정 자리에 두는 버릇이 있어도 찍어서 맞힐 확률이 1/보기 수가 되게).

커밋하지 않는다. 부르는 쪽이 `with get_conn() as conn:` 으로 묶는다.
"""
import json
import random
from datetime import datetime, timezone

from learner import schedule as sc
from learner import state

SOURCE = "review"
# 화면 A(보기 고르기) 가운데 개념 하나만으로 낼 수 있는 종류. 헷갈리는 쌍(이웃 개념 필요)과 화면 B(칩)는 아직 안 낸다
KINDS = ("용어 뜻", "틀린 설명", "O/X")
SHUFFLED = ("용어 뜻", "틀린 설명")  # 보기 순서를 섞는 종류. O/X 는 늘 O, X 순서


class NotDue(Exception):
    """오늘 복습 목록에 없는 개념 (복습일이 아니거나 하루 상한을 다 썼다)."""


class QuizNotFound(LookupError):
    """없는 문제이거나 다른 사용자의 문제."""


class AlreadyAnswered(Exception):
    """이미 답한 문제."""


def pick_kind(issued: int) -> str:
    """이 개념으로 지금까지 낸 복습 문제 수 → 이번에 낼 종류. 0, 1, 2, 3 … → 용어 뜻, 틀린 설명, O/X, 용어 뜻 …"""
    return KINDS[issued % len(KINDS)]


def shuffle_options(content: dict, key: int, rng: random.Random) -> tuple[dict, int]:
    """보기 순서를 섞고 정답 번호를 따라 옮긴다."""
    order = list(range(len(content["options"])))
    rng.shuffle(order)
    return {**content, "options": [content["options"][i] for i in order]}, order.index(key)


def prepare(conn, user_id: str, node_id: int, now: datetime | None = None) -> dict:
    """문제를 내기 전에 확인한다. 아직 안 푼 문제가 있으면 {"pending": 문제}, 없으면 새로 만들 재료
    {"concept", "desc", "kind"} 를 돌려준다. 오늘 복습 목록에 없으면 NotDue."""
    due = state.due_reviews(conn, user_id, now)
    if node_id not in [i["node_id"] for i in due["items"]]:
        raise NotDue(node_id)
    row = conn.execute(
        """SELECT q.id, n.label, q.quiz_kind, q.content, q.guess_p FROM concept_quizzes q
             JOIN concept_nodes n ON n.id = q.node_id
            WHERE q.user_id = %s::uuid AND q.node_id = %s AND q.source = %s AND q.answered_at IS NULL
            ORDER BY q.id DESC LIMIT 1""",
        (user_id, node_id, SOURCE),
    ).fetchone()
    if row:
        return {"pending": _out(row[0], node_id, row[1], row[2], row[3], row[4])}
    label, description, aliases = conn.execute(
        "SELECT label, description, aliases FROM concept_nodes WHERE id = %s", (node_id,)).fetchone()
    (issued,) = conn.execute(
        "SELECT count(*) FROM concept_quizzes WHERE user_id = %s::uuid AND node_id = %s AND source = %s",
        (user_id, node_id, SOURCE),
    ).fetchone()
    return {"concept": label, "desc": description or _term_desc(conn, label, aliases), "kind": pick_kind(issued)}


def save(conn, user_id: str, node_id: int, quiz, rng: random.Random | None = None) -> dict:
    """만든 문제(tutor.quiz.Quiz)를 보관하고 화면용 모양으로 돌려준다. 정답은 돌려주지 않는다."""
    content, key = quiz.content, quiz.key
    if quiz.kind in SHUFFLED:
        content, key = shuffle_options(content, key, rng or random.Random())
    (quiz_id,) = conn.execute(
        """INSERT INTO concept_quizzes (user_id, node_id, source, quiz_kind, guess_p, content, answer_key, explanation)
           VALUES (%s::uuid, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s) RETURNING id""",
        (user_id, node_id, SOURCE, quiz.kind, quiz.guess_p, json.dumps(content, ensure_ascii=False),
         json.dumps(key), quiz.explanation),
    ).fetchone()
    return _out(quiz_id, node_id, quiz.concept, quiz.kind, content, quiz.guess_p)


def answer(conn, user_id: str, quiz_id: int, picked, confidence=None, *, response_ms: int | None = None,
           answer_changes: int | None = None, now: datetime | None = None) -> dict:
    """답 하나를 채점하고 반영한다: 알 확률·복습 일정(state.update) → concept_answers 기록 → 문제에 답한 시각.
    돌려주는 값: {correct, key, explanation, concept, p_know, due_at}."""
    now = now or datetime.now(timezone.utc)
    row = conn.execute(
        """SELECT q.node_id, n.label, q.quiz_kind, q.guess_p, q.content, q.answer_key, q.explanation, q.answered_at
             FROM concept_quizzes q JOIN concept_nodes n ON n.id = q.node_id
            WHERE q.id = %s AND q.user_id = %s::uuid AND q.source = %s FOR UPDATE OF q""",
        (quiz_id, user_id, SOURCE),
    ).fetchone()
    if row is None:
        raise QuizNotFound(quiz_id)
    node_id, label, kind, guess_p, content, key, explanation, answered_at = row
    if answered_at is not None:
        raise AlreadyAnswered(quiz_id)
    correct = picked == key
    p_know = state.update(conn, user_id, label, correct, float(guess_p), confidence, response_ms=response_ms,
                          answer_changes=answer_changes, kind=kind, now=now)
    conn.execute(
        """INSERT INTO concept_answers (user_id, node_id, source, quiz_kind, guess_p, quiz, answer, is_correct,
                                        confidence, response_ms, answer_changes, created_at)
           VALUES (%s::uuid, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s)""",
        (user_id, node_id, SOURCE, kind, guess_p, json.dumps(content, ensure_ascii=False), json.dumps(picked),
         correct, sc.normalize_confidence(confidence), response_ms, answer_changes, now),
    )
    conn.execute("UPDATE concept_quizzes SET answered_at = %s WHERE id = %s", (now, quiz_id))
    (due_at,) = conn.execute(
        "SELECT due_at FROM user_concept_state WHERE user_id = %s::uuid AND node_id = %s", (user_id, node_id)).fetchone()
    return {"correct": correct, "key": key, "explanation": explanation, "concept": label, "p_know": p_know,
            "due_at": due_at}


def _out(quiz_id: int, node_id: int, concept: str, kind: str, content: dict, guess_p: float) -> dict:
    # DB 의 REAL 은 자릿수가 짧아서(0.33333334) 새로 낸 문제와 다시 읽은 문제의 값이 같도록 4자리로 맞춘다
    return {"quiz_id": quiz_id, "node_id": node_id, "concept": concept, "kind": kind, "content": content,
            "guess_p": round(float(guess_p), 4)}


def _term_desc(conn, label: str, aliases: list[str]) -> str:
    """노드에 설명이 없을 때, 카드의 개념 단계가 같은 용어를 풀이한 문장을 찾아 쓴다 (가장 최근 카드). 없으면 빈 글."""
    row = conn.execute(
        """SELECT t->>'desc' FROM steps s, jsonb_array_elements(s.content->'terms') t
            WHERE s.kind = 'concept' AND jsonb_typeof(s.content->'terms') = 'array'
              AND (t->>'term' = %s OR t->>'term' = ANY(%s)) AND coalesce(t->>'desc', '') <> ''
            ORDER BY s.id DESC LIMIT 1""",
        (label, list(aliases or [])),
    ).fetchone()
    return row[0] if row else ""
