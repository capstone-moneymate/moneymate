"""튜터 API (#240): 시작 → 퀴즈 이벤트(정답 없음) → 답 → 채점(정답 포함)·다음 이벤트 → 끝. 실제 모델·DB 없이 본다."""
import uuid

import pytest
from fastapi.testclient import TestClient

import judge_api
from tests.test_tutor_agent import CMAP, TARGETS, fake_quiz, script, text, tool_use
from tutor import agent as ag
from tutor import api as tapi
from tutor.mastery import FakeMastery

USER = str(uuid.uuid4())


@pytest.fixture
def client(monkeypatch):
    tapi.SESSIONS.clear()

    def new_session(user_id, card_id):
        if card_id == 404:
            raise tapi.HTTPException(status_code=404, detail="없는 카드예요.")
        targets = [] if card_id == 0 else TARGETS
        return ag.Session(user_id, CMAP, targets, FakeMastery(), card="자사주 소각 카드", card_id=card_id)

    monkeypatch.setattr(tapi, "new_session", new_session)
    fake_quiz(monkeypatch)
    return TestClient(judge_api.app)


def test_start_answer_done(client, monkeypatch):
    calls = script(monkeypatch,
                   ("tool_use", [tool_use("explain", concept="순이익", style="예시 위주", text="번 돈에서 비용을 뺀 것")]),
                   ("tool_use", [tool_use("ask_quiz", concept="순이익", kind="용어 뜻")]),
                   ("tool_use", [tool_use("go_main")]))
    r = client.post("/tutor/start", json={"user_id": USER, "card_id": 17}).json()
    assert r["status"] == "waiting" and r["targets"] == TARGETS and r["quizzes"] == 1 and r["max_quizzes"] == 6
    assert [e["type"] for e in r["events"]] == ["explain", "quiz"]
    quiz = r["events"][1]
    assert quiz["content"] == {"question": "?", "options": ["a", "b", "c"]} and "key" not in quiz   # 정답은 내려가지 않는다

    a = client.post(f"/tutor/{r['session_id']}/answer", json={"user_id": USER, "answer": 0, "confidence": 2}).json()
    assert [e["type"] for e in a["events"]] == ["graded", "done"]       # 이번 요청에서 새로 생긴 것만
    assert a["events"][0] | {"explanation": "해설"} == {"type": "graded", "concept": "순이익", "kind": "용어 뜻",
                                                      "correct": True, "key": 0, "explanation": "해설"}
    assert a["status"] == "done" and a["finished_by"] == "go_main" and len(calls) == 3

    full = client.get(f"/tutor/{r['session_id']}", params={"user_id": USER}).json()
    assert [e["type"] for e in full["events"]] == ["explain", "quiz", "graded", "done"]   # GET 은 전부


def test_other_user_and_missing_session_are_404(client, monkeypatch):
    script(monkeypatch, ("tool_use", [tool_use("ask_quiz", concept="순이익", kind="용어 뜻")]))
    r = client.post("/tutor/start", json={"user_id": USER, "card_id": 17}).json()
    other = str(uuid.uuid4())
    assert client.post(f"/tutor/{r['session_id']}/answer", json={"user_id": other, "answer": 0}).status_code == 404
    assert client.get(f"/tutor/{r['session_id']}", params={"user_id": other}).status_code == 404
    assert client.post("/tutor/nope/answer", json={"user_id": USER, "answer": 0}).status_code == 404
    assert client.post("/tutor/start", json={"user_id": USER, "card_id": 404}).status_code == 404


def test_answer_when_not_waiting_is_409(client, monkeypatch):
    script(monkeypatch, ("tool_use", [tool_use("go_main")]))
    r = client.post("/tutor/start", json={"user_id": USER, "card_id": 17}).json()
    assert r["status"] == "done"
    res = client.post(f"/tutor/{r['session_id']}/answer", json={"user_id": USER, "answer": 0})
    assert res.status_code == 409


def test_card_without_targets_skips_model(client, monkeypatch):
    script(monkeypatch)   # 모델을 부르면 빈 목록에서 꺼내다 실패한다
    r = client.post("/tutor/start", json={"user_id": USER, "card_id": 0}).json()
    assert r["status"] == "done" and r["finished_by"] == "no_targets" and r["events"] == [{"type": "done", "by": "no_targets"}]


def test_model_failure_still_returns_graded_and_done(client, monkeypatch):
    script(monkeypatch, ("tool_use", [tool_use("ask_quiz", concept="순이익", kind="용어 뜻")]))   # 두 번째 호출은 없음 → 오류
    r = client.post("/tutor/start", json={"user_id": USER, "card_id": 17}).json()
    a = client.post(f"/tutor/{r['session_id']}/answer", json={"user_id": USER, "answer": 1}).json()
    assert [e["type"] for e in a["events"]] == ["graded", "done"] and a["events"][0]["correct"] is False
    assert a["status"] == "error" and a["finished_by"].startswith("stop:")


def test_start_failure_returns_error_done(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("API down")
    monkeypatch.setattr(ag, "create", boom)
    r = client.post("/tutor/start", json={"user_id": USER, "card_id": 17}).json()
    assert r["status"] == "error" and r["events"] == [{"type": "done", "by": "stop:RuntimeError"}]


def test_bad_confidence_is_422(client, monkeypatch):
    script(monkeypatch, ("tool_use", [tool_use("ask_quiz", concept="순이익", kind="용어 뜻")]))
    r = client.post("/tutor/start", json={"user_id": USER, "card_id": 17}).json()
    assert client.post(f"/tutor/{r['session_id']}/answer",
                       json={"user_id": USER, "answer": 0, "confidence": 3}).status_code == 422


def test_prune_old_sessions():
    from datetime import datetime, timedelta, timezone
    tapi.SESSIONS.clear()
    now = datetime.now(timezone.utc)
    old = tapi._Entry(ag.Session("u", CMAP, TARGETS, FakeMastery()))
    old.touched = now - tapi.TTL - timedelta(minutes=1)
    tapi.SESSIONS["old"] = old
    tapi.SESSIONS["new"] = tapi._Entry(ag.Session("u", CMAP, TARGETS, FakeMastery()))
    tapi._prune(now)
    assert list(tapi.SESSIONS) == ["new"]


def test_short_conn_mastery_opens_connection_per_call():
    from tutor.mastery import ShortConnMastery
    opened = []

    class Conn:
        def __enter__(self):
            opened.append(1)
            return self

        def __exit__(self, *a):
            return False

    m = ShortConnMastery(lambda: Conn(), card_id=17)
    import learner.state as st
    orig = st.get_mastery
    st.get_mastery = lambda conn, user: {"순이익": 0.5}
    try:
        assert m.get_mastery("u") == {"순이익": 0.5} and m.get_mastery("u") == {"순이익": 0.5}
    finally:
        st.get_mastery = orig
    assert len(opened) == 2   # 부를 때마다 열고 닫는다 (모델 호출 동안 잡고 있지 않음)
