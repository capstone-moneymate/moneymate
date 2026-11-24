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

    def update_causal(conn, user_id, concept_ids, correct, guess_p):
        seen["update"] = (user_id, concept_ids, correct, guess_p)
        return {c: 0.65 for c in concept_ids if c != "없는_id"}

    def get_mastery(conn, user_id):
        seen["get"] = user_id
        return {"EPS": 0.3, "순이익": 0.88}

    monkeypatch.setattr(api, "_conn", FakeConn)
    monkeypatch.setattr(api.state, "update_causal", update_causal)
    monkeypatch.setattr(api.state, "get_mastery", get_mastery)
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


def test_causal_order_guess(client, calls):
    r = client.post("/learner/answer", json={"user_id": USER, "concept_ids": ["a", "b", "c"],
                                             "correct": False, "kind": "causal_order", "count": 3})
    assert r.status_code == 200
    assert calls["update"][2] is False
    assert calls["update"][3] == pytest.approx(1 / 6)


@pytest.mark.parametrize("patch", [{"user_id": "abc"}, {"kind": "judgement"}, {"count": 0}, {"correct": None}])
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
