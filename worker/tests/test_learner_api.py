"""learner/api.py 테스트. DB 는 가짜 연결로 바꾸고 state 함수가 받은 값을 본다 (state 자체는 test_learner_state.py)."""
import pytest
from fastapi.testclient import TestClient

import judge_api
from learner import api

USER = "11111111-2222-3333-4444-555555555555"


class FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def calls(monkeypatch):
    seen = {}

    def update_causal(conn, user_id, concept_ids, correct, guess_p, **extra):
        seen["update"] = (user_id, concept_ids, correct, guess_p)
        seen["extra"] = extra
        return {c: 0.65 for c in concept_ids if c != "없는_id"}

    def get_mastery(conn, user_id):
        seen["get"] = user_id
        return {"EPS": 0.3, "순이익": 0.88}

    def due_reviews(conn, user_id):
        seen["reviews"] = user_id
        return {"limit": 5, "done_today": 1, "due_total": 7, "items": [
            {"node_id": 3, "concept": "EPS", "p_know": 0.4, "retrievability": 0.81, "reason": "sure_wrong",
             "due_at": "2026-11-24T00:00:00+00:00"}]}

    monkeypatch.setattr(api, "_conn", FakeConn)
    monkeypatch.setattr(api.state, "update_causal", update_causal)
    monkeypatch.setattr(api.state, "get_mastery", get_mastery)
    monkeypatch.setattr(api.state, "due_reviews", due_reviews)
    return seen


@pytest.fixture
def client():
    return TestClient(judge_api.app)   # 채점 서버에 라우터가 붙어 있는지도 함께 본다


def test_guess_hand_calc():
    assert api.guess_for_step("quiz", 4) == 0.25            # 4지선다
    assert api.guess_for_step("chart", 3) == pytest.approx(1 / 3)
    assert api.guess_for_step("causal_order", 3) == pytest.approx(1 / 6)    # 3! = 6
    assert api.guess_for_step("causal_order", 4) == pytest.approx(1 / 24)   # 4! = 24
    with pytest.raises(ValueError):
        api.guess_for_step("judgement", 3)
    with pytest.raises(ValueError):
        api.guess_for_step("quiz", 0)


def test_answer_passes_guess_and_returns_mastery(client, calls):
    r = client.post("/learner/answer", json={"user_id": USER, "concept_ids": ["rate_hold", "없는_id"],
                                             "correct": True, "kind": "quiz", "count": 4})
    assert r.status_code == 200
    assert r.json() == {"guess_p": 0.25, "mastery": {"rate_hold": 0.65}}
    assert calls["update"] == (USER, ["rate_hold", "없는_id"], True, 0.25)
    # 확신·시간을 안 보낸 요청(예전 화면)도 받는다
    assert calls["extra"] == {"confidence": None, "response_ms": None, "answer_changes": None, "kind": "quiz"}


def test_answer_passes_confidence_and_timing(client, calls):
    r = client.post("/learner/answer", json={"user_id": USER, "concept_ids": ["rate_hold"], "correct": True,
                                             "kind": "chart", "count": 3, "confidence": 2, "response_ms": 5300,
                                             "answer_changes": 1})
    assert r.status_code == 200
    assert calls["extra"] == {"confidence": 2, "response_ms": 5300, "answer_changes": 1, "kind": "chart"}


def test_causal_order_guess(client, calls):
    r = client.post("/learner/answer", json={"user_id": USER, "concept_ids": ["a", "b", "c"],
                                             "correct": False, "kind": "causal_order", "count": 3})
    assert r.status_code == 200
    assert calls["update"][2] is False
    assert calls["update"][3] == pytest.approx(1 / 6)


@pytest.mark.parametrize("patch", [{"user_id": "abc"}, {"kind": "judgement"}, {"count": 0}, {"correct": None},
                                   {"confidence": 3}, {"response_ms": -1}, {"answer_changes": -1}])
def test_bad_request_rejected(client, calls, patch):
    body = {"user_id": USER, "concept_ids": ["rate_hold"], "correct": True, "kind": "quiz", "count": 4, **patch}
    assert client.post("/learner/answer", json=body).status_code == 422
    assert "update" not in calls


def test_mastery(client, calls):
    r = client.get(f"/learner/mastery/{USER}")
    assert r.status_code == 200
    assert r.json() == {"mastery": {"EPS": 0.3, "순이익": 0.88}}
    assert calls["get"] == USER
    assert client.get("/learner/mastery/not-a-uuid").status_code == 422


def test_reviews(client, calls):
    r = client.get(f"/learner/reviews/{USER}")
    assert r.status_code == 200
    body = r.json()
    assert (body["limit"], body["done_today"], body["due_total"]) == (5, 1, 7)
    assert body["items"][0]["concept"] == "EPS" and body["items"][0]["reason"] == "sure_wrong"
    assert calls["reviews"] == USER


def test_calibration(client, calls, monkeypatch):
    from learner import calibration as cal

    full = cal.summarize(cal.Table(sure_right=9, sure_wrong=3, unsure_right=3, unsure_wrong=5))
    empty = cal.summarize(cal.Table())

    def report(conn, user_id):
        calls["calibration"] = user_id
        return {"all": full, "recent": full, "earlier": empty, "recent_days": 30, "sure_wrong_concepts": ["EPS"]}

    monkeypatch.setattr(api.state, "calibration_report", report)
    r = client.get(f"/learner/calibration/{USER}")
    assert r.status_code == 200
    body = r.json()
    assert body["all"]["sure_wrong"] == 3 and body["all"]["illusion"] == pytest.approx(0.375)
    assert body["earlier"]["total"] == 0 and body["earlier"]["gamma"] is None      # 분모 0 은 null 로 간다
    assert body["sure_wrong_concepts"] == ["EPS"] and calls["calibration"] == USER


# ---------- 복습 문제 (learner/review.py 는 test_learner_review.py) ----------

QUIZ_OUT = {"quiz_id": 9, "node_id": 3, "concept": "EPS", "kind": "용어 뜻",
            "content": {"question": "EPS 의 뜻은?", "options": ["a", "b", "c"]}, "guess_p": 1 / 3}


@pytest.fixture
def review_calls(monkeypatch):
    seen = {"made": []}

    def make_quiz(kind, concept, desc):
        seen["made"].append((kind, concept, desc))
        return "만든 문제"

    def save(conn, user_id, node_id, quiz):
        seen["saved"] = (user_id, node_id, quiz)
        return QUIZ_OUT

    monkeypatch.setattr(api, "_conn", FakeConn)
    monkeypatch.setattr(api, "make_quiz", make_quiz)
    monkeypatch.setattr(api.review, "save", save)
    return seen


def test_review_quiz_makes_and_saves_new_quiz(client, review_calls, monkeypatch):
    monkeypatch.setattr(api.review, "prepare",
                        lambda conn, user, node: {"concept": "EPS", "desc": "주당순이익", "kind": "용어 뜻"})
    r = client.post("/learner/review/quiz", json={"user_id": USER, "node_id": 3})
    assert r.status_code == 200
    assert r.json() == QUIZ_OUT                       # 정답·해설은 응답에 없다
    assert review_calls["made"] == [("용어 뜻", "EPS", "주당순이익")]
    assert review_calls["saved"] == (USER, 3, "만든 문제")


def test_review_quiz_reuses_pending_without_calling_llm(client, review_calls, monkeypatch):
    monkeypatch.setattr(api.review, "prepare", lambda conn, user, node: {"pending": QUIZ_OUT})
    r = client.post("/learner/review/quiz", json={"user_id": USER, "node_id": 3})
    assert r.status_code == 200 and r.json()["quiz_id"] == 9
    assert review_calls["made"] == [] and "saved" not in review_calls


def test_review_quiz_not_due_is_409(client, review_calls, monkeypatch):
    def not_due(conn, user, node):
        raise api.review.NotDue(node)

    monkeypatch.setattr(api.review, "prepare", not_due)
    r = client.post("/learner/review/quiz", json={"user_id": USER, "node_id": 3})
    assert r.status_code == 409 and review_calls["made"] == []


def test_review_quiz_generation_failure_is_503(client, review_calls, monkeypatch):
    def broken(kind, concept, desc):
        raise RuntimeError("월 한도")

    monkeypatch.setattr(api.review, "prepare",
                        lambda conn, user, node: {"concept": "EPS", "desc": "", "kind": "O/X"})
    monkeypatch.setattr(api, "make_quiz", broken)
    r = client.post("/learner/review/quiz", json={"user_id": USER, "node_id": 3})
    assert r.status_code == 503 and "saved" not in review_calls


def test_review_answer_passes_values_and_maps_errors(client, monkeypatch):
    seen = {}

    def answer(conn, user_id, quiz_id, picked, confidence, **extra):
        seen["args"] = (user_id, quiz_id, picked, confidence, extra)
        if quiz_id == 404:
            raise api.review.QuizNotFound(quiz_id)
        if quiz_id == 409:
            raise api.review.AlreadyAnswered(quiz_id)
        return {"correct": False, "key": 2, "explanation": "해설", "concept": "EPS", "p_know": 0.15,
                "due_at": "2026-11-25T09:00:00+00:00"}

    monkeypatch.setattr(api, "_conn", FakeConn)
    monkeypatch.setattr(api.review, "answer", answer)
    body = {"user_id": USER, "quiz_id": 9, "answer": 1, "confidence": 2, "response_ms": 4200, "answer_changes": 1}
    r = client.post("/learner/review/answer", json=body)
    assert r.status_code == 200
    assert r.json() == {"correct": False, "key": 2, "explanation": "해설", "concept": "EPS", "p_know": 0.15,
                        "due_at": "2026-11-25T09:00:00Z"}
    assert seen["args"] == (USER, 9, 1, 2, {"response_ms": 4200, "answer_changes": 1})
    assert client.post("/learner/review/answer", json=body | {"quiz_id": 404}).status_code == 404
    assert client.post("/learner/review/answer", json=body | {"quiz_id": 409}).status_code == 409
    assert client.post("/learner/review/answer", json=body | {"confidence": 3}).status_code == 422
