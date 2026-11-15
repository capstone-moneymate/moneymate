"""generate/reasons.py 테스트. 실제 API·DB 는 부르지 않는다 (create 를 가짜로, 사전은 작은 그래프)."""
import json
from datetime import date
from types import SimpleNamespace

import pytest

from concepts.graph import build_graph
from generate import reasons as rs
from generate.classify import Concept

CONCEPTS = [Concept("ai_investment", "AI 데이터센터 투자", "AI·반도체", []),
            Concept("gpu_demand", "AI 반도체 수요", "AI·반도체", []),
            Concept("semi_earnings", "반도체 기업 실적", "AI·반도체", []),
            Concept("rate_hike", "기준금리 인상", "금리", [])]
GRAPH = build_graph({c.id: c.name for c in CONCEPTS},
                    [("ai_investment", "gpu_demand", "up"), ("gpu_demand", "semi_earnings", "up")])
BASE = date(2026, 9, 30)
EVIDENCE = [rs.Evidence(1, 11, "2026-09-25", "엔비디아 데이터센터 매출 확대", "NVIDIA", "https://example.com/1"),
            rs.Evidence(2, 12, "2026-08-14", "빅테크 설비투자 계획 상향", None, "https://example.com/2")]
STOCK = {"ticker": "NVDA", "name": "엔비디아"}


def reason(title="AI 투자 확대", body="데이터센터 투자가 늘어 AI 반도체 수요가 커졌을 수 있어요.",
           start="ai_investment", end="semi_earnings", evidence=(1, 2)):
    return {"title": title, "body": body, "start_concept": start, "end_concept": end, "evidence": list(evidence)}


def fake_create(monkeypatch, *payloads, stop="end_turn"):
    """호출 순서대로 응답을 돌려주는 가짜 create. 호출 인자를 모아 돌려준다."""
    queue, calls = list(payloads), []

    def create(module, **kwargs):
        calls.append({"module": module, **kwargs, "messages": list(kwargs["messages"])})
        text = json.dumps({"reasons": queue.pop(0)}, ensure_ascii=False)
        return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)])

    monkeypatch.setattr(rs, "create", create)
    return calls


def run(monkeypatch, *payloads, direction="same", change="up", evidence=EVIDENCE):
    calls = fake_create(monkeypatch, *payloads)
    return rs.generate(STOCK, direction, change, BASE, ["드러켄밀러 +24%"], evidence, CONCEPTS, GRAPH), calls


@pytest.mark.parametrize("direction, change, want", [
    ("same", "up", "왜 다 늘렸을까요?"),
    ("same", "down", "왜 다 줄였을까요?"),
    ("diff", "up", "왜 방향이 다를까요?"),
    ("none", "down", "왜 줄였을까요?"),  # 한쪽만 움직였으면 "다"를 뺀다
])
def test_headline_by_direction(direction, change, want):
    assert rs.headline(direction, change) == want


def test_headline_rejects_unknown():
    with pytest.raises(ValueError):
        rs.headline("mixed", "up")


def test_good_reason_passes_with_code_path(monkeypatch):
    out, calls = run(monkeypatch, [reason()])
    assert out.errors == [] and out.calls == 1 and out.headline == "왜 다 늘렸을까요?"
    r = out.reasons[0]
    assert r.path == ["ai_investment", "gpu_demand", "semi_earnings"]  # 경로는 사전으로 코드가 찾는다
    assert [e.source_id for e in r.evidence] == [11, 12]
    assert calls[0]["module"] == "reasons" and calls[0]["model"] == rs.SONNET


def test_schema_limits_concepts_and_evidence_numbers():
    schema = rs.output_schema(["a", "b"], 3)
    item = schema["properties"]["reasons"]["items"]["properties"]
    assert item["start_concept"]["enum"] == ["a", "b"]
    assert item["evidence"]["items"]["enum"] == [1, 2, 3]  # 입력에 없는 번호는 나올 수 없다


def test_prompt_wraps_sources_as_json():
    user = rs.build_user(STOCK, "same", "up", ["드러켄밀러 +24%"], EVIDENCE)
    assert '"question": "왜 다 늘렸을까요?"' in user
    assert '"no": 2, "date": "2026-08-14"' in user
    assert "ai_investment | AI 데이터센터 투자 | AI·반도체" in rs.build_system(CONCEPTS)


@pytest.mark.parametrize("raw, message", [
    ([], "1~3개"),
    ([reason()] * 4, "1~3개"),
    ([reason(evidence=())], "1개 이상"),
    ([reason(evidence=(3,))], "입력에 없는 근거 번호"),
    ([reason(start="semi_earnings", end="ai_investment")], "경로가 없어요"),
    ([reason(start="gpu_demand", end="gpu_demand")], "같아요"),
    ([reason(title=" ")], "채워 주세요"),
])
def test_check_reasons_errors(raw, message):
    errors = rs.check_reasons(raw, EVIDENCE, BASE, GRAPH)
    assert any(message in e for e in errors), errors


def test_evidence_after_base_date_is_rejected():
    # 기술확정안 "근거 날짜 (탭 2)": 공시 기준일 뒤 자료는 근거가 될 수 없다
    late = EVIDENCE + [rs.Evidence(3, 13, "2026-10-02", "10월 기사", None, "https://example.com/3")]
    errors = rs.check_reasons([reason(evidence=(3,))], late, BASE, GRAPH)
    assert any("공시 기준일(2026-09-30) 뒤" in e for e in errors)


def test_banned_expression_is_rejected():
    errors = rs.check_reasons([reason(body="지금 매수하세요.")], EVIDENCE, BASE, GRAPH)
    assert any("쓰면 안 되는 표현" in e for e in errors), errors


def test_repair_once_then_pass(monkeypatch):
    out, calls = run(monkeypatch, [reason(evidence=())], [reason()])
    assert out.errors == [] and out.calls == 2
    feedback = calls[1]["messages"][-1]["content"]
    assert "근거 자료 번호를 1개 이상" in feedback  # 걸린 이유를 돌려준다


def test_gives_up_after_repair_limit(monkeypatch):
    out, _ = run(monkeypatch, [reason(evidence=())], [reason(evidence=())])
    assert out.reasons == [] and out.calls == rs.MAX_REPAIRS + 1 and out.errors


def test_no_evidence_skips_api(monkeypatch):
    out, calls = run(monkeypatch, evidence=[])
    assert calls == [] and out.calls == 0 and "근거 자료가 없어요" in out.errors[0]


def test_truncated_response_raises(monkeypatch):
    fake_create(monkeypatch, [reason()], stop="max_tokens")
    with pytest.raises(RuntimeError, match="stop_reason=max_tokens"):
        rs.generate(STOCK, "same", "up", BASE, [], EVIDENCE, CONCEPTS, GRAPH)
