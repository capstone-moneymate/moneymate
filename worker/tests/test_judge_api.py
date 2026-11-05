"""judge_api 테스트. 점수 기대값은 test_rule_judge.py 의 손계산 예시와 같다."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import judge_api

CHAIN = [
    {"name": "기준금리 동결", "aliases": ["동결"]},
    {"name": "예대금리차", "aliases": ["이자 마진"]},
    {"name": "은행 실적", "aliases": ["은행 이익"]},
]
FACTS = [
    {"text": "한은 기준금리 3.00% 동결", "keywords": ["3.00%", "3%"]},
    {"text": "4회 연속 동결", "keywords": ["4회 연속", "네 번 연속"]},
]
COUNTER = [{"name": "경기 둔화", "aliases": ["연체"]}]
FULL = ("기준금리가 3%로 4회 연속 동결됐기 때문에 예대금리차가 유지되고, 그래서 은행 실적이 좋아질 것 같아 추가매수를 골랐다. "
        "금리가 계속 동결되는 경우라면 다른 은행주에도 같은 흐름이 이어질 수 있다. "
        "하지만 경기 둔화로 연체가 늘면 은행 이익이 줄 수 있다.")


@pytest.fixture
def client(monkeypatch):
    # judge.py 유무와 상관없이 규칙 채점 경로를 시험한다
    monkeypatch.setattr(judge_api, "_judge", None)
    return TestClient(judge_api.app)


def body(answer, **kw):
    return {"answer": answer, "key_facts": FACTS, "chain": CHAIN, "counter": COUNTER, **kw}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_full_marks(client):
    r = client.post("/judge", json=body(FULL, card_id=1))
    assert r.status_code == 200
    d = r.json()
    # 손계산: 증거 2(사실 2개 + 때문) · 추론 4(경우라면) · 반박 3(경기 둔화, 은행 이익) -> 9/9 -> 100
    assert d["rubric"] == {"evidence": 2, "reasoning": 4, "rebuttal": 3}
    assert d["total"] == 9 and d["score"] == 100
    assert d["grader"] == "rule"
    assert d["matched_concepts"] == ["기준금리 동결", "예대금리차", "은행 실적"]


def test_concepts_without_connective(client):
    d = client.post("/judge", json=body("금리가 동결돼서 은행 실적이 좋아질 것 같다.")).json()
    # 손계산: 증거 0 · 추론 2(개념 2개, 연결어 없음) · 반박 0 -> 2/9 -> 22
    assert d["rubric"] == {"evidence": 0, "reasoning": 2, "rebuttal": 0}
    assert d["score"] == 22


def test_counter_is_optional(client):
    r = client.post("/judge", json={"answer": "3% 동결, 4회 연속.", "key_facts": FACTS, "chain": CHAIN})
    assert r.status_code == 200
    # 손계산: 증거 1(사실 2개, 연결어 없음) · 추론 1(개념 1개) -> 2/9 -> 22
    assert r.json()["rubric"] == {"evidence": 1, "reasoning": 1, "rebuttal": 0}


@pytest.mark.parametrize("bad", [
    {"answer": ""},                                   # 빈 근거
    {"answer": "가" * (judge_api.MAX_ANSWER_CHARS + 1)},  # 너무 긴 근거
    {"answer": "동결", "chain": [{"aliases": ["x"]}]},  # 개념 이름 없음
    {},                                               # answer 없음
])
def test_invalid_request_is_422(client, bad):
    assert client.post("/judge", json=bad).status_code == 422


def test_uses_judge_when_present(monkeypatch):
    calls = []

    def fake_grade(text, key_facts, chain, counter, card_id=None):
        calls.append(card_id)
        return SimpleNamespace(rubric={"evidence": 1, "reasoning": 3, "rebuttal": 2}, total=6, score=67,
                               matched_facts=["x"], matched_concepts=["y"])

    monkeypatch.setattr(judge_api, "_judge", SimpleNamespace(grade=fake_grade))
    d = TestClient(judge_api.app).post("/judge", json=body("아무 근거", card_id=7)).json()
    assert calls == [7]
    assert d["grader"] == "claude" and d["score"] == 67


def test_falls_back_to_rule_when_judge_raises(monkeypatch):
    def broken(**_):
        raise RuntimeError("Claude 실패")

    monkeypatch.setattr(judge_api, "_judge", SimpleNamespace(grade=broken))
    d = TestClient(judge_api.app).post("/judge", json=body(FULL)).json()
    assert d["grader"] == "rule"
    assert d["score"] == 100
