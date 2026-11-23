"""학습자 지식 상태 저장 (사람2, 계획 2-3). 계산은 learner/bkt.py, 여기서는 user_concept_state 를 읽고 쓴다.

개념은 concept_nodes 의 노드다 (009). 사람1 튜터와 맞춘 모양 (worker/tutor/mastery.py 의 FakeMastery 자리):
    get_mastery(conn, user_id)                       -> {개념 이름(label): 알 확률}
    update(conn, user_id, concept, correct, guess_p) -> 새 알 확률
본 문제(steps)의 답은 개념이 인과 사전 id(steps.content.concept_ids)로 오므로 update_causal 로 넣는다.

커밋하지 않는다. 부르는 쪽이 `with get_conn() as conn:` 으로 묶는다 (답 기록과 함께 저장되거나 함께 취소되게).
"""
import logging

from learner import bkt

log = logging.getLogger(__name__)


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


def update(conn, user_id: str, concept: str, correct: bool, guess_p: float,
           confidence=None, params: bkt.Params = bkt.DEFAULT) -> float:
    """개념 퀴즈 답 하나를 반영하고 새 알 확률을 돌려준다. concept 은 노드 이름(label).
    confidence 는 BKT 가 쓰지 않는다 (알 확률은 정답과 추측 확률로만 고친다). FSRS(2-4)가 쓸 자리라 받아만 둔다."""
    row = conn.execute("SELECT id FROM concept_nodes WHERE label = %s", (concept,)).fetchone()
    if row is None:
        raise UnknownConcept(concept)
    return _apply(conn, user_id, row[0], correct, guess_p, params)


def update_causal(conn, user_id: str, causal_ids: list[str], correct: bool, guess_p: float,
                  params: bkt.Params = bkt.DEFAULT) -> dict[str, float]:
    """본 문제(퀴즈·차트 읽기·인과 순서) 답 하나를 그 단계의 인과 사전 개념마다 반영한다. {인과 사전 id: 새 알 확률}.
    인과 사전 개념의 노드가 없으면 만든다 (이름이 같은 노드가 있으면 그 노드에 잇는다). 사전에 없는 id 는 건너뛴다."""
    out = {}
    for cid in dict.fromkeys(c.strip() for c in causal_ids if c and c.strip()):  # 같은 id 는 한 번만, 순서 유지
        node_id = _causal_node(conn, cid)
        if node_id is None:
            log.warning("개념 노드를 찾거나 만들지 못해 건너뛰어요: %s", cid)
            continue
        out[cid] = _apply(conn, user_id, node_id, correct, guess_p, params)
    return out


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


def _apply(conn, user_id: str, node_id: int, correct: bool, guess_p: float, params: bkt.Params) -> float:
    conn.execute("INSERT INTO users (id) VALUES (%s::uuid) ON CONFLICT (id) DO NOTHING", (user_id,))
    # 행을 먼저 만들고 잠근 뒤 고친다 (같은 사용자의 답 두 개가 동시에 와도 하나씩 반영되게)
    conn.execute(
        """INSERT INTO user_concept_state (user_id, node_id, p_know) VALUES (%s::uuid, %s, %s)
           ON CONFLICT (user_id, node_id) DO NOTHING""",
        (user_id, node_id, params.p_init),
    )
    (p,) = conn.execute(
        "SELECT p_know FROM user_concept_state WHERE user_id = %s::uuid AND node_id = %s FOR UPDATE",
        (user_id, node_id),
    ).fetchone()
    new = bkt.update(float(p), bool(correct), guess_p, params)
    conn.execute(
        """UPDATE user_concept_state SET p_know = %s, last_review_at = now(), updated_at = now()
            WHERE user_id = %s::uuid AND node_id = %s""",
        (new, user_id, node_id),
    )
    return new
