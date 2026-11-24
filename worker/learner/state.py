"""학습자 상태 저장 (사람2, 계획 2-3·2-4). 계산은 learner/bkt.py(알 확률)와 learner/schedule.py(복습 일정)가 하고,
여기서는 user_concept_state 를 읽고 쓴다. 답 하나가 들어오면 알 확률과 복습 일정을 함께 고친다.

개념은 concept_nodes 의 노드다 (009). 사람1 튜터와 맞춘 모양 (worker/tutor/mastery.py 의 FakeMastery 자리):
    get_mastery(conn, user_id)                       -> {개념 이름(label): 알 확률}
    update(conn, user_id, concept, correct, guess_p) -> 새 알 확률
본 문제(steps)의 답은 개념이 인과 사전 id(steps.content.concept_ids)로 오므로 update_causal 로 넣는다.
due_reviews 는 오늘 복습할 개념 목록, calibration_report 는 확신 보정(2-5)용 2 × 2 표와 지표다.

커밋하지 않는다. 부르는 쪽이 `with get_conn() as conn:` 으로 묶는다 (답 기록과 함께 저장되거나 함께 취소되게).
"""
import logging
from datetime import datetime, timedelta, timezone

from learner import bkt
from learner import calibration as cal
from learner import schedule as sc

log = logging.getLogger(__name__)

PAST_TIMES = 50   # "빨랐나"를 볼 때 비교하는 지난 응답 수 (최근 것부터)
RECENT_DAYS = 30  # 확신 보정에서 "최근"으로 보는 날 수 (계획: "한 달 전보다 과신이 줄었어요")


class UnknownConcept(LookupError):
    """concept_nodes 에 없는 개념 이름."""


def get_mastery(conn, user_id: str, params: bkt.Params = bkt.DEFAULT) -> dict[str, float]:
    """개념 지도의 모든 개념에 대한 알 확률. 아직 안 풀어 본 개념은 처음 값(p_init)이다."""
    rows = conn.execute(
        """SELECT n.label, COALESCE(s.p_know, %s)
             FROM concept_nodes n
             LEFT JOIN user_concept_state s ON s.node_id = n.id AND s.user_id = %s::uuid
            ORDER BY n.id""",
        (params.p_init, user_id),
    ).fetchall()
    return {label: float(p) for label, p in rows}


def update(conn, user_id: str, concept: str, correct: bool, guess_p: float, confidence=None,
           params: bkt.Params = bkt.DEFAULT, *, response_ms: int | None = None, answer_changes: int | None = None,
           kind: str | None = None, now: datetime | None = None) -> float:
    """개념 퀴즈(튜터·복습) 답 하나를 반영하고 새 알 확률을 돌려준다. concept 은 노드 이름(label).
    confidence 는 1 헷갈려요 / 2 확실해요 (화면 글자로 와도 된다). 알 확률(BKT)은 정답과 추측 확률로만 고치고,
    확신·응답 시간·답 변경은 복습 일정(FSRS 자동 평가)에 쓴다. kind 는 퀴즈 종류 (같은 종류끼리 응답 시간을 비교)."""
    row = conn.execute("SELECT id FROM concept_nodes WHERE label = %s", (concept,)).fetchone()
    if row is None:
        raise UnknownConcept(concept)
    past = _past_quiz_times(conn, user_id, kind) if response_ms is not None and kind else []
    return _apply(conn, user_id, row[0], correct, guess_p, params, confidence=confidence, response_ms=response_ms,
                  answer_changes=answer_changes, past_ms=past, now=now)


def update_causal(conn, user_id: str, causal_ids: list[str], correct: bool, guess_p: float,
                  params: bkt.Params = bkt.DEFAULT, *, confidence=None, response_ms: int | None = None,
                  answer_changes: int | None = None, kind: str | None = None,
                  now: datetime | None = None) -> dict[str, float]:
    """본 문제(퀴즈·차트 읽기·인과 순서) 답 하나를 그 단계의 인과 사전 개념마다 반영한다. {인과 사전 id: 새 알 확률}.
    인과 사전 개념의 노드가 없으면 만든다 (이름이 같은 노드가 있으면 그 노드에 잇는다). 사전에 없는 id 는 건너뛴다.
    kind 는 단계 종류(quiz / chart / causal_order). 같은 종류를 맞혔던 지난 응답 시간과 비교해 "빨랐나"를 본다."""
    past = _past_step_times(conn, user_id, kind) if response_ms is not None and kind else []
    out = {}
    for cid in dict.fromkeys(c.strip() for c in causal_ids if c and c.strip()):  # 같은 id 는 한 번만, 순서 유지
        node_id = _causal_node(conn, cid)
        if node_id is None:
            log.warning("개념 노드를 찾거나 만들지 못해 건너뛰어요: %s", cid)
            continue
        out[cid] = _apply(conn, user_id, node_id, correct, guess_p, params, confidence=confidence,
                          response_ms=response_ms, answer_changes=answer_changes, past_ms=past, now=now)
    return out


def due_reviews(conn, user_id: str, now: datetime | None = None, limit: int = sc.DAILY_LIMIT) -> dict:
    """오늘 복습할 개념. 복습일(due_at)이 오늘(KST)이거나 지난 개념 중에서 하루 상한만큼 고른다.
    순서: ① 확실해요라고 했는데 틀린 개념 (최근 것부터) ② 나머지는 지금 기억 확률이 낮은 것부터.
    상한은 개념 수 기준이고, 오늘 이미 복습한 개념 수(concept_answers 의 review)를 뺀다.
    돌려주는 값: {limit, done_today, due_total, items: [{node_id, concept, p_know, retrievability, reason, due_at}]}"""
    now = now or datetime.now(timezone.utc)
    rows = conn.execute(
        """SELECT n.id, n.label, s.p_know, s.stability, s.difficulty, s.last_review_at, s.due_at, s.sure_wrong_at
             FROM user_concept_state s
             JOIN concept_nodes n ON n.id = s.node_id
            WHERE s.user_id = %s::uuid
              AND s.stability IS NOT NULL
              AND (s.due_at AT TIME ZONE 'Asia/Seoul')::date <= (%s::timestamptz AT TIME ZONE 'Asia/Seoul')::date""",
        (user_id, now),
    ).fetchall()
    (done_today,) = conn.execute(
        """SELECT count(DISTINCT node_id) FROM concept_answers
            WHERE user_id = %s::uuid AND source = 'review'
              AND (created_at AT TIME ZONE 'Asia/Seoul')::date = (%s::timestamptz AT TIME ZONE 'Asia/Seoul')::date""",
        (user_id, now),
    ).fetchone()
    items = []
    for node_id, label, p_know, stability, difficulty, last_review, due, sure_wrong in rows:
        memory = sc.Memory(float(stability), float(difficulty), last_review, due)
        items.append({
            "node_id": node_id, "concept": label, "p_know": float(p_know),
            "retrievability": sc.retrievability(memory, now),
            "reason": "sure_wrong" if sure_wrong is not None else "due",
            "due_at": due, "_sure_wrong_at": sure_wrong,
        })
    # ① 확실해요 + 틀림이 먼저(최근 것부터) ② 기억 확률 낮은 순. 같으면 노드 id 순 (돌릴 때마다 같게)
    items.sort(key=lambda i: (0, -i["_sure_wrong_at"].timestamp(), i["node_id"]) if i["_sure_wrong_at"] is not None
               else (1, i["retrievability"], i["node_id"]))
    for i in items:
        del i["_sure_wrong_at"]
    remaining = max(0, limit - done_today)
    return {"limit": limit, "done_today": done_today, "due_total": len(items), "items": items[:remaining]}


def confidence_table(conn, user_id: str, since: datetime | None = None, until: datetime | None = None) -> cal.Table:
    """확신을 누른 답의 2 × 2 개수 (정답/오답 × 확실/헷갈려요). 본 문제(user_answers)와 개념 퀴즈(concept_answers)를 합친다.
    확신 없이 낸 답(판단해보기, 예전 화면)은 세지 않는다. since 이상 until 미만의 답만 센다 (없으면 전체)."""
    rows = conn.execute(
        """SELECT a.confidence, a.is_correct, count(*)
             FROM (SELECT confidence, is_correct, created_at FROM user_answers
                    WHERE user_id = %(u)s::uuid AND confidence IS NOT NULL AND is_correct IS NOT NULL
                   UNION ALL
                   SELECT confidence, is_correct, created_at FROM concept_answers
                    WHERE user_id = %(u)s::uuid AND confidence IS NOT NULL) a
            WHERE (%(since)s::timestamptz IS NULL OR a.created_at >= %(since)s::timestamptz)
              AND (%(until)s::timestamptz IS NULL OR a.created_at < %(until)s::timestamptz)
            GROUP BY a.confidence, a.is_correct""",
        {"u": user_id, "since": since, "until": until},
    ).fetchall()
    n = {(int(conf), bool(ok)): int(count) for conf, ok, count in rows}
    return cal.Table(sure_right=n.get((sc.SURE, True), 0), sure_wrong=n.get((sc.SURE, False), 0),
                     unsure_right=n.get((sc.UNSURE, True), 0), unsure_wrong=n.get((sc.UNSURE, False), 0))


def calibration_report(conn, user_id: str, now: datetime | None = None, recent_days: int = RECENT_DAYS) -> dict:
    """마이페이지 확신 보정 카드용. {all, recent, earlier, recent_days, sure_wrong_concepts}.
    all = 전체, recent = 최근 recent_days 일, earlier = 그 전. recent 와 earlier 를 비교해 "과신이 줄었나"를 본다.
    sure_wrong_concepts = 확실해요라고 했는데 틀렸고 아직 다시 맞히지 못한 개념 이름 (최근 것부터)."""
    now = now or datetime.now(timezone.utc)
    cut = now - timedelta(days=recent_days)
    labels = conn.execute(
        """SELECT n.label FROM user_concept_state s JOIN concept_nodes n ON n.id = s.node_id
            WHERE s.user_id = %s::uuid AND s.sure_wrong_at IS NOT NULL
            ORDER BY s.sure_wrong_at DESC, n.id""",
        (user_id,),
    ).fetchall()
    return {
        "all": cal.summarize(confidence_table(conn, user_id, until=now)),
        "recent": cal.summarize(confidence_table(conn, user_id, since=cut, until=now)),
        "earlier": cal.summarize(confidence_table(conn, user_id, until=cut)),
        "recent_days": recent_days,
        "sure_wrong_concepts": [r[0] for r in labels],
    }


def _past_step_times(conn, user_id: str, kind: str) -> list[int]:
    """같은 종류의 본 문제를 맞혔던 지난 응답 시간 (ms, 최근 PAST_TIMES 개)."""
    rows = conn.execute(
        """SELECT ua.response_ms FROM user_answers ua JOIN steps s ON s.id = ua.step_id
            WHERE ua.user_id = %s::uuid AND s.kind = %s AND ua.is_correct AND ua.response_ms IS NOT NULL
            ORDER BY ua.id DESC LIMIT %s""",
        (user_id, kind, PAST_TIMES),
    ).fetchall()
    return [r[0] for r in rows]


def _past_quiz_times(conn, user_id: str, kind: str) -> list[int]:
    """같은 종류의 개념 퀴즈를 맞혔던 지난 응답 시간 (ms, 최근 PAST_TIMES 개)."""
    rows = conn.execute(
        """SELECT response_ms FROM concept_answers
            WHERE user_id = %s::uuid AND quiz_kind = %s AND is_correct AND response_ms IS NOT NULL
            ORDER BY id DESC LIMIT %s""",
        (user_id, kind, PAST_TIMES),
    ).fetchall()
    return [r[0] for r in rows]


def _causal_node(conn, causal_id: str) -> int | None:
    row = conn.execute("SELECT id FROM concept_nodes WHERE causal_id = %s", (causal_id,)).fetchone()
    if row:
        return row[0]
    # 이름이 같은 노드가 이미 있으면(개념 단계 용어로 먼저 생긴 것) 새로 만들지 않고 그 노드에 잇는다.
    # 그 노드가 벌써 다른 인과 개념에 이어져 있으면 아무것도 돌아오지 않는다 → 건너뜀
    row = conn.execute(
        """INSERT INTO concept_nodes (label, aliases, causal_id)
           SELECT name, aliases, id FROM concepts WHERE id = %s
           ON CONFLICT (label) DO UPDATE SET causal_id = EXCLUDED.causal_id, updated_at = now()
            WHERE concept_nodes.causal_id IS NULL
           RETURNING id""",
        (causal_id,),
    ).fetchone()
    return row[0] if row else None


def _apply(conn, user_id: str, node_id: int, correct: bool, guess_p: float, params: bkt.Params, *,
           confidence=None, response_ms: int | None = None, answer_changes: int | None = None,
           past_ms: list[int] | None = None, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    correct = bool(correct)
    conf = sc.normalize_confidence(confidence)
    conn.execute("INSERT INTO users (id) VALUES (%s::uuid) ON CONFLICT (id) DO NOTHING", (user_id,))
    # 행을 먼저 만들고 잠근 뒤 고친다 (같은 사용자의 답 두 개가 동시에 와도 하나씩 반영되게)
    conn.execute(
        """INSERT INTO user_concept_state (user_id, node_id, p_know) VALUES (%s::uuid, %s, %s)
           ON CONFLICT (user_id, node_id) DO NOTHING""",
        (user_id, node_id, params.p_init),
    )
    p, stability, difficulty, last_review, due = conn.execute(
        """SELECT p_know, stability, difficulty, last_review_at, due_at FROM user_concept_state
            WHERE user_id = %s::uuid AND node_id = %s FOR UPDATE""",
        (user_id, node_id),
    ).fetchone()

    # 1. 알 확률 (BKT): 정답과 추측 확률로만
    new_p = bkt.update(float(p), correct, guess_p, params)

    # 2. 복습 일정 (FSRS): 정답·확신·응답 시간·답 변경으로 평가를 정한다
    memory = None if stability is None else sc.Memory(float(stability), float(difficulty), last_review, due)
    rating = sc.rate(correct, conf, sc.is_fast(response_ms, past_ms or []), answer_changes)
    memory = sc.review(memory, rating, now)

    # 3. 확실해요인데 틀렸으면 시각을 남기고(복습 맨 앞), 맞히면 지운다. 헷갈려요로 틀린 것은 그대로 둔다
    sure_wrong = (not correct) and conf == sc.SURE
    conn.execute(
        """UPDATE user_concept_state
              SET p_know = %s, stability = %s, difficulty = %s, fsrs_state = 2, fsrs_step = NULL,
                  last_review_at = %s, due_at = %s, updated_at = now(),
                  sure_wrong_at = CASE WHEN %s THEN %s::timestamptz WHEN %s THEN NULL ELSE sure_wrong_at END
            WHERE user_id = %s::uuid AND node_id = %s""",
        (new_p, memory.stability, memory.difficulty, memory.last_review, memory.due,
         sure_wrong, now, correct, user_id, node_id),
    )
    return new_p
