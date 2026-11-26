"""튜터 에이전트 API (사람1, #240). 채점 서버(judge_api.py)에 붙는 라우터다. Spring 이 로그인 사용자를 확인한 뒤 부른다.

- POST /tutor/start              카드의 개념 단계 튜터를 시작한다. 퀴즈를 낼 때까지(또는 끝날 때까지) 돌고 이벤트를 돌려준다
- POST /tutor/{session_id}/answer 기다리는 퀴즈의 답을 낸다. 채점 → 알 확률·답 기록까지 하고 graded 를 바로 돌려준다(status running).
                                 다음 퀴즈(또는 끝)는 뒤에서 만들고, 화면은 GET 으로 받아 간다 (#281)
- GET  /tutor/{session_id}        지금 상태와 지금까지의 이벤트 전부 (화면을 새로 열었을 때)

이벤트 (tutor/agent.py 가 만든다. 화면은 순서대로 그린다)
- explain {concept, definition, detail, example} 짧은 설명. 정의·보충·예시 칸이 따로다 (example 은 빈 문자열일 수 있다)
- quiz    {kind, concept, content, guess_p}      퀴즈. content 는 화면용이고 정답이 없다 (정답은 이 서버 메모리에만)
- graded  {concept, kind, correct, key, explanation}  채점 결과. 답한 뒤라 정답(key)을 같이 준다
- done    {by}                                    끝 (go_main: 본 문제로 / quiz_limit / call_limit / no_tool / stop:오류 / no_targets)
응답의 events 는 이번 요청에서 새로 생긴 것만이다 (GET 은 전부).

세션은 이 서버 메모리에 둔다 (SESSIONS). 서버를 다시 켜면 사라지고, 화면은 개념 단계를 건너뛰고 본 문제로 가면 된다.
DB 연결은 알 확률을 읽고 답을 기록할 때만 잠깐 연다 (ShortConnMastery). 모델 호출은 한 요청에 여러 번이라 몇 초~수십 초 걸릴 수 있다.
"""
import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tutor import agent as ag
from tutor.mastery import ShortConnMastery

log = logging.getLogger(__name__)

router = APIRouter(prefix="/tutor", tags=["tutor"])

TTL = timedelta(hours=2)   # 이만큼 안 쓴 세션은 지운다
MAX_SESSIONS = 500         # 메모리 상한. 넘으면 오래된 것부터 지운다


class _Entry:
    def __init__(self, s: ag.Session):
        self.s = s
        self.seen = 0
        self.lock = threading.Lock()   # 같은 세션에 답이 두 번 동시에 오지 않게
        self.touched = datetime.now(timezone.utc)


SESSIONS: dict[str, _Entry] = {}
_STORE_LOCK = threading.Lock()


def _connect():
    # psycopg 를 여기서 불러온다. judge_api 를 띄우는 것만으로는 DB 가 필요 없게 (learner/api.py 와 같다)
    from db import get_conn

    return get_conn()


def _prune(now: datetime) -> None:
    for sid in [k for k, e in SESSIONS.items() if now - e.touched > TTL]:
        SESSIONS.pop(sid, None)
    while len(SESSIONS) >= MAX_SESSIONS:
        SESSIONS.pop(min(SESSIONS, key=lambda k: SESSIONS[k].touched))


def _get(session_id: str, user_id: UUID) -> _Entry:
    e = SESSIONS.get(session_id)
    if e is None or e.s.user != str(user_id):   # 남의 세션도 없는 세션처럼 (있는지조차 알리지 않는다)
        raise HTTPException(status_code=404, detail="없는 튜터 세션이에요.")
    return e


class StartIn(BaseModel):
    user_id: UUID
    card_id: int


class AnswerIn(BaseModel):
    user_id: UUID
    answer: Any = Field(description="고른 보기 번호(0부터), 칩 빈칸은 빈칸 순서대로 칩 번호, 짝 맞추기는 용어 순서대로 뜻 번호, "
                                    "사례 분류는 사례 순서대로 바구니 번호")
    confidence: int | None = Field(default=None, ge=1, le=2, description="1 헷갈려요, 2 확실해요. 없으면 비움")
    response_ms: int | None = Field(default=None, ge=0)
    answer_changes: int | None = Field(default=None, ge=0)


class TutorOut(BaseModel):
    session_id: str
    status: str = Field(description="waiting(퀴즈 답 기다림) / running(다음 퀴즈를 만드는 중) / done / error")
    finished_by: str | None
    targets: list[str] = Field(description="이 카드의 목표 개념 (개념 단계 용어)")
    quizzes: int
    max_quizzes: int
    events: list[dict]


def _out(sid: str, e: _Entry, all_events: bool = False) -> TutorOut:
    s = e.s
    status = s.status   # 상태를 이벤트보다 먼저 읽는다: agent 가 이벤트를 넣은 뒤 상태를 바꾸므로 waiting·done 이면 그 이벤트가 있다
    events = s.events if all_events else s.events[e.seen:]
    if not all_events:
        e.seen = len(s.events)
    return TutorOut(session_id=sid, status=status, finished_by=s.finished_by, targets=s.targets, quizzes=s.quizzes,
                    max_quizzes=s.max_quizzes, events=list(events))


def new_session(user_id: str, card_id: int) -> ag.Session:
    """카드의 지도·목표 개념·제목을 DB 에서 읽어 세션을 만든다 (모델은 아직 부르지 않는다)."""
    with _connect() as conn:
        cmap = ag.ConceptMap.from_db(conn)
        targets = ag.card_targets(conn, card_id)
        row = conn.execute("SELECT title FROM cards WHERE id = %s", (card_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="없는 카드예요.")
    return ag.Session(user_id, cmap, targets, ShortConnMastery(_connect, card_id), card=row[0], card_id=card_id)


@router.post("/start", response_model=TutorOut)
def start(req: StartIn) -> TutorOut:
    s = new_session(str(req.user_id), req.card_id)
    sid = uuid.uuid4().hex
    e = _Entry(s)
    with _STORE_LOCK:
        _prune(e.touched)
        SESSIONS[sid] = e
    if not s.targets:   # 개념 단계 용어가 지도에 없는 카드: 모델을 부르지 않고 바로 본 문제로
        s.status, s.finished_by = "done", "no_targets"
        s.events.append({"type": "done", "by": "no_targets"})
        return _out(sid, e)
    with e.lock:
        try:
            ag.start(s)
        except Exception as ex:   # 모델 오류·월 한도 등: agent 가 세션을 error 로 끝내고 done 이벤트를 남겼다
            log.warning("튜터를 시작하지 못했어요 (카드 %s): %s", req.card_id, ex)
        return _out(sid, e)


@router.post("/{session_id}/answer", response_model=TutorOut)
def answer(session_id: str, req: AnswerIn) -> TutorOut:
    """채점 결과(graded)를 먼저 돌려주고(status running), 다음 퀴즈(모델 호출 몇 번, 수 초)는 뒤에서 만든다 (#281).
    화면은 사용자가 해설을 보는 동안 GET 으로 다음 이벤트를 받아 간다. 잠금은 뒤 작업이 끝날 때 풀린다 (그동안 답이 오면 409)."""
    e = _get(session_id, req.user_id)
    if not e.lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="앞의 답을 처리하고 있어요.")
    background = False
    try:
        e.touched = datetime.now(timezone.utc)
        if e.s.status != "waiting" or not e.s.pending:
            raise HTTPException(status_code=409, detail="기다리는 퀴즈가 없어요.")
        # 지금까지의 이벤트(뒤에서 만든 다음 퀴즈 포함)는 화면이 GET 으로 이미 받았다. 이 답의 응답에는 채점 결과만 담는다
        e.seen = len(e.s.events)
        try:
            ag.grade(e.s, req.answer, req.confidence, response_ms=req.response_ms, answer_changes=req.answer_changes)
        except Exception as ex:   # 채점·기록 실패(DB 등): 기록 전이면 새 이벤트 없이 waiting 그대로,
                                  # 기록 뒤 상태 읽기에서 실패했으면 graded 와 done(stop:...) 으로 끝난 세션을 돌려준다
            log.warning("답을 채점하지 못했어요 (세션 %s): %s", session_id, ex)
            return _out(session_id, e)
        out = _out(session_id, e)   # graded 만, status running
        threading.Thread(target=_resume, args=(session_id, e), daemon=True).start()
        background = True           # 잠금은 _resume 이 푼다
        return out
    finally:
        if not background:
            e.lock.release()


def _resume(session_id: str, e: _Entry) -> None:
    try:
        ag.resume(e.s)
    except Exception as ex:   # 다음 모델 호출이 실패했다: agent 가 세션을 error 로 끝내고 done(stop:...) 이벤트를 남겼다
        log.warning("튜터를 이어 가지 못했어요 (세션 %s): %s", session_id, ex)
    finally:
        e.touched = datetime.now(timezone.utc)
        e.lock.release()


@router.get("/{session_id}", response_model=TutorOut)
def get(session_id: str, user_id: UUID) -> TutorOut:
    return _out(session_id, _get(session_id, user_id), all_events=True)
