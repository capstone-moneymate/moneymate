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
            Concept("rate_hike", "기준금리 인상", "금리", []),
            Concept("bond_yield", "국채 금리", "금리", []),
            Concept("growth_valuation", "성장주 가치평가", "금리", [])]
# rate_hike → growth_valuation: 직접 ▼ 와 국채 금리 경유 (+1)(+1) = ▲ 가 함께 있는 모호한 쌍 (테스트용으로 만든 연결)
GRAPH = build_graph({c.id: c.name for c in CONCEPTS},
                    [("ai_investment", "gpu_demand", "up"), ("gpu_demand", "semi_earnings", "up"),
                     ("rate_hike", "growth_valuation", "down"), ("rate_hike", "bond_yield", "up"),
                     ("bond_yield", "growth_valuation", "up"),
                     ("rate_hike", "semi_earnings", "down")])
BASE = date(2026, 9, 30)
EVIDENCE = [rs.Evidence(1, 11, "2026-09-25", "엔비디아 데이터센터 매출 확대", "NVIDIA", "https://example.com/1"),
            rs.Evidence(2, 12, "2026-08-14", "빅테크 설비투자 계획 상향", None, "https://example.com/2")]
STOCK = {"ticker": "NVDA", "name": "엔비디아"}


def reason(title="AI 투자 확대", body="데이터센터 투자가 늘어 AI 반도체 수요가 커졌을 수 있어요.",
           start="ai_investment", end="semi_earnings", evidence=(1, 2), change=None):
    r = {"title": title, "body": body, "start_concept": start, "end_concept": end, "evidence": list(evidence)}
    if change:  # 없으면 예전 응답 모양 (change 칸 없음 → up 으로 계산)
        r["change"] = change
    return r


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
    assert r.direction == "up"  # (+1)(+1): 투자가 늘면 실적에 올리는 힘
    assert [e.source_id for e in r.evidence] == [11, 12]
    assert calls[0]["module"] == "reasons" and calls[0]["model"] == rs.SONNET


def test_schema_limits_concepts_and_evidence_numbers():
    schema = rs.output_schema(["a", "b"], 3)
    item = schema["properties"]["reasons"]["items"]["properties"]
    assert item["start_concept"]["enum"] == ["a", "b"]
    assert item["evidence"]["items"]["enum"] == [1, 2, 3]  # 입력에 없는 번호는 나올 수 없다
    # 시작 개념의 변화 (5주차 노션 제안 (1))
    assert item["change"]["enum"] == ["up", "down"]
    assert "change" in schema["properties"]["reasons"]["items"]["required"]


def test_rate_event_start_needs_that_decision_in_evidence():
    # 동결뿐인 분기에 rate_hike(down) 으로 "인상이 없었다"를 돌려 쓰지 못하게 한다
    hold = rs.Evidence(1, 21, "2026-06-17", "FOMC 정책금리 결정", None, "u", {"decision": "hold"})
    hike = rs.Evidence(2, 22, "2026-09-16", "FOMC 정책금리 결정", None, "u", {"decision": "hike"})
    base = date(2026, 9, 30)
    via_hold = reason("금리 인상 없음", "금리가 그대로라 부담이 덜했을 수 있어요.", "rate_hike", "growth_valuation",
                      evidence=(1,), change="down")
    errors = rs.check_reasons([via_hold], [hold, hike], base, GRAPH)
    assert any("실제 'hike' 결정이 있을 때만" in e for e in errors)
    # 실제 인상 근거가 있고 change 가 up 이면 통과 (경로 검사는 테스트 그래프가 모호한 쌍이라 bond_yield 로 본다)
    ok = reason("금리 인상", "금리가 올라 부담이 커졌을 수 있어요.", "rate_hike", "bond_yield", evidence=(2,), change="up")
    assert rs.check_reasons([ok], [hold, hike], base, GRAPH) == []
    # 인상 근거여도 change 가 down 이면 막는다
    bad = reason("금리 인상", "본문이에요.", "rate_hike", "bond_yield", evidence=(2,), change="down")
    assert rs.check_reasons([bad], [hold, hike], base, GRAPH)


def test_rate_hold_is_not_a_start_concept():
    # B 결정: 금리 동결은 조건 붙은 연결·모든 종목에 같은 이유·양이 아닌 사건이라 이유의 시작으로 쓰지 않는다
    item = rs.output_schema(["rate_hold", "rate_hike", "growth_valuation"], 2)["properties"]["reasons"]["items"]
    assert item["properties"]["start_concept"]["enum"] == ["rate_hike", "growth_valuation"]
    assert "rate_hold" in item["properties"]["end_concept"]["enum"]  # 끝 개념으로는 쓸 수 있다


def test_change_down_flips_direction_and_matches_reduction(monkeypatch):
    # "AI 투자가 줄어 실적에 누르는 힘 → 줄였다": change 가 없으면 (+1)(+1) = ▲ 로 계산돼 줄임과 반대였다
    down = reason("AI 투자 둔화", "투자가 줄어 수요가 약해졌을 수 있어요.", change="down")
    out, _ = run(monkeypatch, [down], change="down")
    r = out.reasons[0]
    assert (r.change, r.direction) == ("down", "down") and out.warnings == []
    # 예전 응답(칸 없음)은 up 으로 계산 → 줄임 종목과 반대라 다시 쓰게 하고, 맞게 고치면 통과한다 (아래 테스트들)


def test_direction_mismatch_retries_once_then_passes(monkeypatch):
    # 2026-11-18 B 제안: 방향이 반대면 "큰손 방향과 맞는 경로만" 한 번 다시 쓰게 한다
    fixed = reason("AI 투자 둔화", "투자가 줄어 수요가 약해졌을 수 있어요.", change="down")
    out, calls = run(monkeypatch, [reason()], [fixed], change="down")
    assert out.errors == [] and out.calls == 2 and out.warnings == []
    assert [r.title for r in out.reasons] == ["AI 투자 둔화"]
    feedback = calls[1]["messages"][-1]["content"]
    assert "큰손은 이 종목을 줄임했어요" in feedback
    assert "ai_investment(up) → semi_earnings 힘이 up 인데 큰손은 줄임" in feedback


def test_direction_mismatch_after_retry_drops_only_wrong_reasons(monkeypatch):
    # 다시 써도 반대인 이유는 빼고, 맞는 이유는 살린다. 뺀 까닭은 warnings 에 남는다 (status 는 published)
    good = reason("AI 투자 둔화", "투자가 줄어 수요가 약해졌을 수 있어요.", change="down")
    wrong = reason("호실적 뒤 차익 실현", "실적이 좋아 판 것일 수 있어요.")
    out, calls = run(monkeypatch, [good, wrong], [good, wrong], change="down")
    assert out.calls == 1 + rs.MAX_DIRECTION_RETRIES and out.errors == []
    assert [r.title for r in out.reasons] == ["AI 투자 둔화"]
    assert len(out.warnings) == 1 and "호실적 뒤 차익 실현" in out.warnings[0]


def test_direction_mismatch_with_no_matching_reason_is_rejected(monkeypatch):
    # MU·AAPL·COHR "호실적 뒤 차익 실현" 같은 경우: 맞는 이유가 하나도 없으면 errors → save 가 rejected
    wrong = reason("호실적 뒤 차익 실현", "실적이 좋아 판 것일 수 있어요.")
    out, _ = run(monkeypatch, [wrong], [wrong], change="down")
    assert out.reasons == [] and out.errors == ["큰손 변화와 방향이 맞는 이유가 없어요"]
    assert len(out.warnings) == 1


def test_diff_stock_does_not_retry_for_direction(monkeypatch):
    # 엇갈린 종목은 어느 쪽 이유든 되므로 다시 쓰게 하지 않는다
    out, calls = run(monkeypatch, [reason()], direction="diff", change="down")
    assert out.errors == [] and len(out.reasons) == 1 and len(calls) == 1


class _Conn:
    def __init__(self):
        self.params = None

    def execute(self, sql, params=None):
        self.params = params


@pytest.mark.parametrize("reasons, errors, want", [
    (["r"], [], "published"),
    ([], ["큰손 변화와 방향이 맞는 이유가 없어요"], "rejected"),
    ([], [], "rejected"),
])
def test_save_status_has_no_pending(reasons, errors, want):
    # 방향 경고가 있어도 pending 으로 두지 않는다 (뺀 이유는 model_info.warnings 에만)
    r = rs.Reason("t", "b", "ai_investment", "semi_earnings", [], "up", [], "up")
    result = rs.ReasonsResult("왜 다 줄였을까요?", [r] if reasons else [], errors, warnings=["뺀 이유"])
    conn = _Conn()
    assert rs.save(conn, BASE, "MU", "same", "down", result, None) == want
    assert want in conn.params


def test_change_flips_direction_on_single_edge():
    # 테스트 그래프의 bond_yield → growth_valuation 은 올리는 연결(up). 시작이 커지면 ▲, 줄어들면 ▼
    assert rs.path_and_direction(GRAPH, "bond_yield", "growth_valuation", "down") == (["bond_yield", "growth_valuation"], "down")
    assert rs.path_and_direction(GRAPH, "bond_yield", "growth_valuation") == (["bond_yield", "growth_valuation"], "up")


def test_direction_warnings_skip_diff_and_list_mismatches():
    r_up = rs.Reason("a", "b", "ai_investment", "semi_earnings", [], "up", [], "up")
    r_down = rs.Reason("c", "d", "ai_investment", "semi_earnings", [], "down", [], "down")
    assert rs.direction_warnings([r_up, r_down], "diff", "up") == []  # 엇갈린 종목은 보지 않는다
    warn = rs.direction_warnings([r_up, r_down], "same", "up")
    assert len(warn) == 1 and warn[0].startswith("이유 2 'c'")
    assert len(rs.direction_warnings([r_up, r_down], "none", "down")) == 1


def test_prompt_wraps_sources_as_json():
    user = rs.build_user(STOCK, "same", "up", ["드러켄밀러 +24%"], EVIDENCE)
    assert '"question": "왜 다 늘렸을까요?"' in user
    assert '"no": 2, "date": "2026-08-14"' in user
    assert "ai_investment | AI 데이터센터 투자 | AI·반도체" in rs.build_system(CONCEPTS)
    assert '"numbers"' not in user  # numbers 가 없는 근거는 칸을 넣지 않는다


def test_prompt_passes_evidence_numbers_without_calendar_flag():
    # FOMC 동결을 제목만 보고 "금리 부담이 줄었다"로 지어낸 문제 (2026-11-16) → 결정·금리 전후를 넘긴다
    fomc = rs.Evidence(1, 21, "2026-06-17", "FOMC 정책금리 결정", None, "https://example.com/f",
                       {"calendar_verified": True, "decision": "hold", "rate_before": 3.75, "rate_after": 3.75})
    user = rs.build_user(STOCK, "same", "up", [], [fomc])
    assert '"numbers": {' in user and '"decision": "hold"' in user and '"rate_after": 3.75' in user
    assert "calendar_verified" not in user
    system = rs.build_system(CONCEPTS)
    assert "hold(동결)" in system and "hold 면 금리가 바뀌지 않은 것" in system


@pytest.mark.parametrize("ticker,market", [("NVDA", "US"), ("BRK-B", "US"), ("005930", "KR"), ("00104K", "KR"),
                                           ("0015B0", "KR")])
def test_stock_market_for_macro_filter(ticker, market):
    # 미국 종목 근거에 한국은행 결정이 들어간 문제 (2026-11-16) → 시장에 맞는 지수 키의 거시 발표만
    assert rs.stock_market(ticker) == market
    assert rs.MACRO_INDEXES[market] == (["US500", "IXIC"] if market == "US" else ["KS11", "KQ11"])


@pytest.mark.parametrize("raw, message", [
    ([], "1~3개"),
    ([reason()] * 4, "1~3개"),
    ([reason(evidence=())], "1개 이상"),
    ([reason(evidence=(3,))], "입력에 없는 근거 번호"),
    ([reason(start="semi_earnings", end="ai_investment")], "경로가 없어요"),
    ([reason(start="gpu_demand", end="gpu_demand")], "같아요"),
    ([reason(title=" ")], "채워 주세요"),
    ([reason(start="rate_hike", end="growth_valuation")], "경로마다 방향이 달라요"),  # 모호한 쌍 (#85 리뷰)
])
def test_check_reasons_errors(raw, message):
    errors = rs.check_reasons(raw, EVIDENCE, BASE, GRAPH)
    assert any(message in e for e in errors), errors


def test_down_path_keeps_direction(monkeypatch):
    # 누르는 힘 경로도 통과하되 방향을 담아 화면이 ▼ 를 그릴 수 있게 한다
    # rate_hike 는 근거에 실제 인상 결정이 있어야 시작 개념이 된다 (DECISION_EVENTS)
    hike = [rs.Evidence(1, 31, "2026-09-16", "FOMC 정책금리 결정", None, "u", {"decision": "hike"})]
    # 큰손 방향 검사(늘림인데 ▼ 이유 → 다시 쓰기)와 섞이지 않게 엇갈린(diff) 종목으로 본다
    out, _ = run(monkeypatch, [reason(start="rate_hike", end="semi_earnings", evidence=(1,))], evidence=hike,
                 direction="diff")
    assert out.errors == [] and out.reasons[0].direction == "down"
    assert out.reasons[0].path == ["rate_hike", "semi_earnings"]


def test_same_evidence_twice_is_rejected_by_b_checker():
    # 근거 검사는 B의 check_evidence (#130). 바꿔 끼우면서 새로 생긴 검사: 같은 번호를 두 번 고르면 걸린다
    errors = rs.check_reasons([reason(evidence=(1, 1))], EVIDENCE, BASE, GRAPH)
    assert errors == ["이유 1: 근거 1 를 두 번 골랐어요. 한 번만 쓰세요"]


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


def test_keeps_passing_reasons_after_repair_limit(monkeypatch):
    # 끝까지 한 이유만 걸리면 그 이유만 빼고 나머지는 살린다 (사전에 없는 경로 하나 때문에 통째로 rejected 되던 문제)
    bad = reason("없는 경로", "본문이에요.", start="growth_valuation", end="ai_investment")
    out, _ = run(monkeypatch, [reason(), bad], [reason(), bad])
    assert out.errors == [] and len(out.reasons) == 1 and out.reasons[0].title == "AI 투자 확대"
    assert len(out.dropped) == 1 and "경로가 없어요" in out.dropped[0]


def test_no_evidence_skips_api(monkeypatch):
    out, calls = run(monkeypatch, evidence=[])
    assert calls == [] and out.calls == 0 and "근거 자료가 없어요" in out.errors[0]


def test_truncated_response_raises(monkeypatch):
    fake_create(monkeypatch, [reason()], stop="max_tokens")
    with pytest.raises(RuntimeError, match="stop_reason=max_tokens"):
        rs.generate(STOCK, "same", "up", BASE, [], EVIDENCE, CONCEPTS, GRAPH)
