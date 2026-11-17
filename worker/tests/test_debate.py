"""debate.py (판단해보기 피드백용 낙관·비관 토론). 네트워크·DB 없이 손으로 정한 예시로 본다."""
import json
from types import SimpleNamespace

import pytest

from generate import debate as db_

INP = db_.DebateInput(
    card_id=7,
    title="한국은행 기준금리 2.50% 동결",
    question="은행 ETF 를 어떻게 하시겠어요?",
    context="기준금리가 4연속 동결됐어요.",
    choices=["추가 매수", "관망", "비중 축소"],
    key_facts=["기준금리 2.50% 동결", "4연속 동결"],
    slides=[{"heading": "금리 동결", "body": "한국은행이 기준금리를 묶었어요.", "facts": [{"label": "금리", "value": "2.50%"}]}],
    chain=["기준금리", "예대금리차", "은행 실적"],
    counter=["경기 둔화"],
)
PAYLOAD = db_.facts_payload(INP)

BULL_OK = "기준금리 동결 → 예대금리차 유지 → 은행 실적 순서로 이어져요. 이자 이익을 지키는 데 도움이 될 수 있어요."
BEAR_OK = "낙관 쪽은 예대금리차만 봤어요. 경기 둔화로 연체가 늘면 은행 실적에 부담이 될 수 있어요."


# --- 코드 검사 ---

def test_check_text_passes_numbers_from_input():
    # 2.50 과 2.5 는 같은 숫자 (끝자리 0 무시), 4 는 key_facts 에 있다
    assert db_.check_text("금리가 2.5%에서 4번째로 묶였어요.", PAYLOAD) == []


def test_check_text_rejects_new_number():
    errs = db_.check_text("은행 이익이 12% 늘 수 있어요.", PAYLOAD)
    assert errs == ["입력에 없는 숫자를 썼어요: 12"]


def test_check_text_rejects_banned_phrase():
    errs = db_.check_text("은행주는 앞으로 오를 것이에요.", PAYLOAD)
    assert len(errs) == 1 and errs[0].startswith("쓰면 안 되는 표현이 있어요")


def test_check_text_rejects_choice_name_ignoring_spaces():
    # "비중 축소" 를 "비중축소" 로 붙여 써도 걸린다
    errs = db_.check_text("지금은 비중축소가 나아 보여요.", PAYLOAD)
    assert errs == ["판단해보기 선택지 이름을 썼어요: 비중 축소"]


def test_check_text_length_and_empty():
    assert db_.check_text("   ", PAYLOAD) == ["문장이 비어 있어요"]
    assert db_.check_text("가" * db_.MAX_CHARS, PAYLOAD) == []
    assert db_.check_text("가" * (db_.MAX_CHARS + 1), PAYLOAD) == [f"{db_.MAX_CHARS}자 안쪽 2~3문장으로 줄여 주세요"]


# --- 낙관 → 비관 ---

def fake_create(monkeypatch, *texts, stop="end_turn"):
    queue, calls = list(texts), []

    def create(module, **kwargs):
        calls.append({"module": module, **kwargs, "messages": list(kwargs["messages"])})
        body = json.dumps({"text": queue.pop(0)}, ensure_ascii=False)
        return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=body)])

    monkeypatch.setattr(db_, "create", create)
    return calls


def test_build_bull_then_bear_published(monkeypatch):
    calls = fake_create(monkeypatch, BULL_OK, BEAR_OK)
    res = db_.build(INP)
    assert (res.bull, res.bear, res.calls, res.errors, res.status) == (BULL_OK, BEAR_OK, 2, [], "published")
    assert [c["module"] for c in calls] == ["debate", "debate"]
    assert [c["note"] for c in calls] == ["side=bull", "side=bear"]
    assert all(c["card_id"] == 7 and c["model"] == db_.HAIKU for c in calls)
    assert calls[0]["system"] == db_.BULL_SYSTEM and calls[1]["system"] == db_.BEAR_SYSTEM
    # 비관은 낙관 발언을 받아 반박한다
    assert f"<bull>{BULL_OK}</bull>" in calls[1]["messages"][0]["content"]
    assert "<bull>" not in calls[0]["messages"][0]["content"]


def test_build_repairs_bull_once(monkeypatch):
    calls = fake_create(monkeypatch, "은행 이익이 12% 늘 수 있어요.", BULL_OK, BEAR_OK)
    res = db_.build(INP)
    assert res.status == "published" and res.calls == 3
    # 두 번째 낙관 호출에 앞의 답과 고칠 까닭이 들어간다
    repair = calls[1]["messages"]
    assert repair[1]["role"] == "assistant" and "12%" in repair[1]["content"]
    assert "입력에 없는 숫자를 썼어요: 12" in repair[2]["content"]


def test_build_bull_fails_skips_bear(monkeypatch):
    calls = fake_create(monkeypatch, "지금 관망하세요.", "관망이 좋아요.")
    res = db_.build(INP)
    assert res.status == "rejected" and res.bull is None and res.bear is None
    assert res.calls == 2 and len(calls) == 2  # MAX_REPAIRS=1 → 낙관 2번, 비관은 안 부름
    assert res.errors == ["낙관: 판단해보기 선택지 이름을 썼어요: 관망"]


def test_build_bear_fails_keeps_bull(monkeypatch):
    fake_create(monkeypatch, BULL_OK, "은행주는 내릴 것이에요.", "은행주는 내릴 것이에요.")
    res = db_.build(INP)
    assert res.status == "rejected" and res.bull == BULL_OK and res.bear is None and res.calls == 3
    assert len(res.errors) == 1 and res.errors[0].startswith("비관: 쓰면 안 되는 표현이 있어요")


def test_cut_off_response_raises(monkeypatch):
    fake_create(monkeypatch, BULL_OK, stop="max_tokens")
    with pytest.raises(RuntimeError, match="stop_reason=max_tokens"):
        db_.build(INP)


# --- DB 읽기·쓰기 (가짜 연결) ---

class FakeConn:
    def __init__(self, row=None):
        self.row, self.sql = row, []

    def execute(self, sql, params=None):
        self.sql.append((sql, params))
        return SimpleNamespace(fetchone=lambda: self.row, fetchall=lambda: [])


def test_load_input_maps_concept_ids_to_names():
    row = ("제목", [{"heading": "h", "body": "b", "facts": []}], [{"text": "사실1", "keywords": ["k"]}],
           {"question": "Q", "context": "C", "choices": ["A", "B"]},
           {"chain": ["rate", "nim"], "counter": ["slowdown", "unknown_id"]})
    names = {"rate": "기준금리", "nim": "예대금리차", "slowdown": "경기 둔화"}
    inp = db_.load_input(FakeConn(row), 3, names)
    assert (inp.card_id, inp.question, inp.choices, inp.key_facts) == (3, "Q", ["A", "B"], ["사실1"])
    assert inp.chain == ["기준금리", "예대금리차"]
    assert inp.counter == ["경기 둔화", "unknown_id"]  # 사전에 없는 id 는 그대로


def test_load_input_without_judgement_step():
    assert db_.load_input(FakeConn(None), 3, {}) is None


def test_save_upserts_status_and_model_info():
    conn = FakeConn()
    db_.save(conn, db_.DebateResult(7, BULL_OK, BEAR_OK, calls=2))
    sql, params = conn.sql[0]
    assert "ON CONFLICT (card_id) DO UPDATE" in sql
    assert params[:4] == (7, BULL_OK, BEAR_OK, "published")
    assert params[4].obj == {"model": db_.HAIKU, "calls": 2, "errors": []}


def test_status_rejected_when_errors_even_with_text():
    assert db_.DebateResult(7, BULL_OK, BEAR_OK, errors=["x"]).status == "rejected"
