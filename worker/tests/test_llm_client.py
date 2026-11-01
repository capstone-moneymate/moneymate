"""generate/llm_client.py 테스트. 실제 API·DB 는 부르지 않는다 (가짜 클라이언트, DB 실패 → jsonl)."""
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import psycopg
import pytest

import config
from generate import llm_client


def usage(inp=0, out=0, cw=0, cr=0):
    return SimpleNamespace(
        input_tokens=inp, output_tokens=out, cache_creation_input_tokens=cw, cache_read_input_tokens=cr
    )


@pytest.fixture
def no_db(monkeypatch, tmp_path):
    """DB 연결은 늘 실패하고, jsonl 은 임시 폴더에 쓴다."""

    def fail():
        raise psycopg.OperationalError("no db in tests")

    monkeypatch.setattr(llm_client, "get_conn", fail)
    monkeypatch.setattr(llm_client, "LOG_PATH", tmp_path / "llm_cost_log.jsonl")
    return tmp_path / "llm_cost_log.jsonl"


# --- 비용 계산 (손계산) ---

def test_cost_haiku_basic():
    # 입력 1,000 × $0.10/1M + 출력 200 × $0.50/1M = 0.0001 + 0.0001 = 0.0002
    assert llm_client.cost_usd("claude-haiku-5-5", usage(1000, 200)) == pytest.approx(0.0002)


def test_cost_sonnet_basic():
    # 입력 10,000 × $2/1M + 출력 2,000 × $10/1M = 0.02 + 0.02 = 0.04
    assert llm_client.cost_usd("claude-sonnet-5-5", usage(10_000, 2_000)) == pytest.approx(0.04)


def test_cost_sonnet_with_cache():
    # 입력 1,000×2 + 캐시쓰기 4,000×2×1.25 + 캐시읽기 10,000×2×0.1 = 2,000 + 10,000 + 2,000 = 14,000
    # 출력 500×10 = 5,000 → (14,000 + 5,000)/1M = 0.019
    assert llm_client.cost_usd("claude-sonnet-5-5", usage(1000, 500, cw=4000, cr=10_000)) == pytest.approx(0.019)


def test_cost_haiku_long_context():
    # 입력 120,000 > 100K → 긴 입력 단가: 120,000×0.50 + 1,000×2.50 = 60,000 + 2,500 → 0.0625
    assert llm_client.cost_usd("claude-haiku-5-5", usage(120_000, 1_000)) == pytest.approx(0.0625)


def test_cost_unknown_model():
    with pytest.raises(ValueError):
        llm_client.cost_usd("claude-unknown", usage(1, 1))


# --- 이번 달 시작 (KST) ---

def test_month_start_uses_kst():
    # UTC 10/31 16:00 = KST 11/1 01:00 → 11월
    start = llm_client.month_start(datetime(2026, 10, 31, 16, 0, tzinfo=timezone.utc))
    assert (start.year, start.month, start.day, start.hour) == (2026, 11, 1, 0)


# --- 한도 확인 (jsonl 대체 경로) ---

def test_month_spent_from_jsonl_counts_this_month_only(no_db):
    rows = [
        {"called_at": "2026-10-31T14:59:00+00:00", "cost_usd": 1.0},  # KST 10/31 23:59 → 지난달
        {"called_at": "2026-10-31T15:00:00+00:00", "cost_usd": 0.25},  # KST 11/1 00:00 → 이번 달
        {"called_at": "2026-11-05T00:00:00+00:00", "cost_usd": 0.5},
    ]
    no_db.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    now = datetime(2026, 11, 10, tzinfo=timezone.utc)
    assert llm_client.month_spent(now) == pytest.approx(0.75)


def test_check_budget_blocks_at_limit(monkeypatch):
    monkeypatch.setattr(config, "LLM_MONTHLY_LIMIT_USD", 10.0)
    monkeypatch.setattr(llm_client, "month_spent", lambda now=None: 10.0)
    with pytest.raises(llm_client.BudgetExceeded):
        llm_client.check_budget()


def test_check_budget_passes_under_limit(monkeypatch):
    monkeypatch.setattr(config, "LLM_MONTHLY_LIMIT_USD", 10.0)
    monkeypatch.setattr(llm_client, "month_spent", lambda now=None: 9.99)
    assert llm_client.check_budget() == pytest.approx(9.99)


# --- create: 한도 → 호출 → 기록 ---

class FakeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **params):
        self.calls.append(params)
        return SimpleNamespace(
            model=params["model"],
            usage=usage(1000, 200),
            content=[
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text="안녕"),
            ],
            stop_reason="end_turn",
            _request_id="req_test",
        )


@pytest.fixture
def fake_client(monkeypatch):
    messages = FakeMessages()
    monkeypatch.setattr(llm_client, "get_client", lambda: SimpleNamespace(messages=messages))
    return messages


def test_create_records_cost(no_db, fake_client, monkeypatch):
    monkeypatch.setattr(config, "LLM_MONTHLY_LIMIT_USD", 10.0)
    resp = llm_client.create(
        "classify", card_id=7, model="claude-haiku-5-5", max_tokens=256, messages=[{"role": "user", "content": "x"}]
    )
    assert llm_client.text_of(resp) == "안녕"
    assert fake_client.calls[0]["max_tokens"] == 256  # params 는 그대로 전달

    row = json.loads(no_db.read_text(encoding="utf-8").strip())
    assert row["module"] == "classify"
    assert row["card_id"] == 7
    assert row["input_tokens"] == 1000 and row["output_tokens"] == 200
    assert row["cost_usd"] == pytest.approx(0.0002)
    assert "request_id=req_test" in row["note"]


def test_create_blocked_does_not_call_api(fake_client, monkeypatch):
    monkeypatch.setattr(config, "LLM_MONTHLY_LIMIT_USD", 10.0)
    monkeypatch.setattr(llm_client, "month_spent", lambda now=None: 12.0)
    with pytest.raises(llm_client.BudgetExceeded):
        llm_client.create("compose", model="claude-sonnet-5-5", max_tokens=10, messages=[])
    assert fake_client.calls == []
