"""generate/compose.py 테스트. 실제 API·DB 는 부르지 않는다 (create·가격을 가짜로 바꾼다)."""
import copy
import json
from datetime import date, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from generate import compose as cp
from generate import tools
from generate.classify import ClassifyResult, load_concepts

SOURCE = {
    "id": 11, "source_type": "macro", "source_key": "bok_2026_10", "title": "한국은행 기준금리 3.00% 동결",
    "url": "https://www.bok.or.kr/", "category": "bok_rate", "issuer_name": "한국은행", "ticker": "KS11",
    "published_date": date(2026, 10, 8), "numbers": {"기준금리": "3.00%"},
}
CLS2 = ClassifyResult(2, "rate_hold", "동결")


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """DB 없음: 개념은 seeds, ETF 는 빈 목록, 가격은 가짜 표, 도구 로그는 임시 폴더."""
    import psycopg

    def fail():
        raise psycopg.OperationalError("no db in tests")

    from generate import classify
    monkeypatch.setattr(classify, "get_conn", fail)
    monkeypatch.setattr(cp, "get_conn", fail)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "tool_calls.jsonl")

    # 2026-09-01 부터 평일 30일, 종가 100,101,... 거래량은 마지막 날만 3000
    days, d = [], date(2026, 9, 1)
    while len(days) < 30:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    full = pd.DataFrame({"market_date": days, "close": [100.0 + i for i in range(30)],
                         "volume": [1000] * 29 + [3000]})
    monkeypatch.setattr(tools, "load_prices", lambda t, end, n: full[full["market_date"] <= end].tail(n).reset_index(drop=True))
    return full


def good_card(prices) -> dict:
    last = str(prices.iloc[-1].market_date)
    return {
        "title": "한국은행, 기준금리 동결",
        "slides": [
            {"label": "무슨 일이 있었나요?", "heading": "기준금리를 그대로 뒀어요", "body": "동결했어요.",
             "facts": [{"label": "기준금리", "value": "3.00%"}]},
            {"label": "오늘의 결론", "heading": "업종마다 달라요", "body": "순서로 정리해 봐요.", "facts": []},
        ],
        "key_facts": [{"text": "기준금리 3.00% 동결", "keywords": ["동결", "3.00%", "3%"]},
                      {"text": "성장주 가치평가 부담", "keywords": ["성장주"]}],
        "steps": [
            {"kind": "concept", "concept_ids": ["rate_hold"], "title": "기준금리", "body": "출발점이에요.",
             "terms": [{"term": "동결", "desc": "그대로 둠"}]},
            {"kind": "quiz", "concept_ids": ["rate_hold"], "question": "동결은?", "options": ["올림", "내림", "그대로"],
             "answer_index": 2, "explanation": "그대로 둔다는 뜻이에요."},
            {"kind": "causal_order", "concept_ids": ["rate_hold", "growth_valuation"], "question": "순서대로",
             "items": [{"concept_id": "rate_hold", "label": "금리 동결"},
                       {"concept_id": "growth_valuation", "label": "성장주 가치평가"}],
             "causal": {"start_concept": "rate_hold", "change": "up", "end_concept": "growth_valuation",
                        "answer_order": ["rate_hold", "growth_valuation"], "direction": "down",
                        "evidence_quote": "한국은행 기준금리 3.00% 동결"},
             "explanation": "할인율이 높게 유지돼요."},
            {"kind": "chart", "concept_ids": ["volume_spike"], "question": "평균의 몇 배?", "ticker": "KS11",
             "options": ["1배", "2배", "3배"], "answer_index": 2, "explanation": "3배였어요.",
             "chart_check": {"metric": "volume_ratio", "start_date": None, "end_date": last, "value": "3"}},
            {"kind": "judgement", "concept_ids": ["rate_hold", "growth_valuation"], "question": "무엇을 지켜볼까요?",
             "context": "고른 답은 채점하지 않아요.", "choices": ["은행주", "기술주", "아직 판단하기 어렵다"],
             "chain": ["rate_hold", "growth_valuation"], "counter": []},
        ],
    }


@pytest.fixture
def ids():
    return {c.id for c in load_concepts()}


CTX = tools.ToolContext(source_text=cp.source_text(SOURCE), ref="macro:bok_2026_10")


# --- 검증 ---

def test_good_card_passes(offline, ids):
    assert cp.validate_card(good_card(offline), 2, ids, CTX) == []


@pytest.mark.parametrize("break_it, expect", [
    (lambda c: c["steps"].pop(2), "단계 순서"),
    (lambda c: c["slides"].pop(), "2~3장"),
    (lambda c: c["key_facts"][0].update(keywords=[]), "key_facts"),
    (lambda c: c["slides"][0].update(body="은행주를 사세요."), "사세요"),
    (lambda c: c["slides"][1].update(body="성장주가 상승할 전망이에요."), "상승할 전망"),
    (lambda c: c["steps"][1].update(answer_index=3), "보기 범위 밖"),
    (lambda c: c["steps"][2]["causal"].update(direction="up"), "방향"),
    (lambda c: c["steps"][2]["causal"].update(evidence_quote="금리를 내렸다"), "원문에 없음"),
    (lambda c: c["steps"][2].update(concept_ids=["growth_valuation", "rate_hold"]), "정답 순서 그대로"),
    (lambda c: c["steps"][3]["chart_check"].update(value="2.5"), "코드가 계산한 값은 3.0"),
    # chart_check 는 맞는데 answer_index 가 다른 보기를 가리킴 (리뷰 #45)
    (lambda c: c["steps"][3].update(answer_index=1), "정답 보기(1번 '2배')에 코드가 확인한 값 3.0 이 없어요"),
    (lambda c: c["steps"][3].update(options=["3배", "3.0배", "1배"], answer_index=0), "보기 여러 개(0, 1번)"),
    (lambda c: c["steps"][3]["chart_check"].update(end_date="2026-09-06"), "확인할 수 없어요"),  # 일요일
    (lambda c: c["steps"][4].update(chain=[]), "chain"),
    (lambda c: c["steps"][0].update(concept_ids=["moon"]), "사전에 없는 개념"),
    # judgement 의 chain·counter 도 사전과 대조 (리뷰 #45, A의 채점이 이 id 로 개념 이름을 찾는다)
    (lambda c: c["steps"][4].update(chain=["rate_hold", "moon"]), "5단계(judgement): 사전에 없는 개념 moon"),
    (lambda c: c["steps"][4].update(counter=["recession"]), "5단계(judgement): 사전에 없는 개념 recession"),
])
def test_bad_cards_fail(offline, ids, break_it, expect):
    card = good_card(offline)
    break_it(card)
    errors = cp.validate_card(card, 2, ids, CTX)
    assert any(expect in e for e in errors), errors


@pytest.mark.parametrize("text", [
    "메모리를 만드는 회사라.",            # 예전 FORBIDDEN 의 '사라' 오탐 (B 요청 1)
    "한국은행의 목표가 물가 안정이에요.",  # '목표가' 오탐
])
def test_banned_uses_validators_no_false_positive(offline, ids, text):
    card = good_card(offline)
    card["slides"][0]["body"] = text
    assert cp.validate_card(card, 2, ids, CTX) == []


def test_problem_text_is_question_plus_options():
    assert cp.problem_text("동결은?", ["올림", "내림", "그대로"]) == "동결은? 올림 내림 그대로"


def test_duplicate_quiz_fails(offline, ids):
    card = good_card(offline)
    past = [cp.problem_text("동결은?", ["올림", "내림", "그대로"])]
    errors = cp.validate_card(card, 2, ids, CTX, past)
    assert any("거의 같아요" in e and "동결은?" in e for e in errors), errors


def test_judgement_question_not_checked_for_duplicates(offline, ids):
    card = good_card(offline)
    # 판단해보기 질문과 똑같은 예전 문장이 있어도 걸리지 않는다 (B와 합의: 판단 질문은 빼고 넘긴다)
    past = [card["steps"][4]["question"], "전혀 다른 퀴즈 질문 하나 둘 셋"]
    assert cp.validate_card(card, 2, ids, CTX, past) == []
    assert cp.card_problem_texts(card) == ["동결은? 올림 내림 그대로",
                                          "평균의 몇 배? 1배 2배 3배"]


def test_type3_order(offline, ids):
    card = good_card(offline)
    card["steps"] = [card["steps"][0], card["steps"][4]]
    assert cp.validate_card(card, 3, ids, CTX) == []


# --- DB 행 ---

def test_step_rows(offline):
    rows = cp.step_rows(good_card(offline), seed="bok_2026_10")
    assert [r["kind"] for r in rows] == cp.STEP_ORDER[2] and [r["step_no"] for r in rows] == [1, 2, 3, 4, 5]
    quiz = rows[1]
    assert quiz["answer"] == {"correct": 2, "explanation": "그대로 둔다는 뜻이에요."}
    assert "answer_index" not in quiz["content"]  # 정답은 content 에 없다
    order = rows[2]
    assert [i["concept_id"] for i in order["content"]["items"]] == ["growth_valuation", "rate_hold"]  # 정답과 다르게 섞임
    assert order["answer"]["correct"] == ["rate_hold", "growth_valuation"]
    assert rows[3]["content"]["ticker"] == "KS11" and rows[3]["answer"]["check"]["metric"] == "volume_ratio"
    # 차트 표시 기간 (B 요청 5): 끝 = 확인한 날, 시작 = 90일 앞 (start_date 없음)
    last = date.fromisoformat(str(offline.iloc[-1].market_date))
    assert rows[3]["content"]["end_date"] == last.isoformat()
    assert rows[3]["content"]["start_date"] == (last - timedelta(days=90)).isoformat()
    assert rows[4]["answer"] == {"chain": ["rate_hold", "growth_valuation"], "counter": []}
    assert rows[0]["answer"] is None


@pytest.mark.parametrize("check, want", [
    # 확인 기간이 짧으면 90일 앞부터
    ({"start_date": "2026-10-01", "end_date": "2026-10-08"}, ("2026-07-10", "2026-10-08")),
    # 확인 기간이 90일보다 길면 확인 기간 시작부터
    ({"start_date": "2026-05-01", "end_date": "2026-10-08"}, ("2026-05-01", "2026-10-08")),
    ({"start_date": None, "end_date": "2026-10-08"}, ("2026-07-10", "2026-10-08")),
])
def test_chart_display_range(check, want):
    r = cp.chart_display_range(check)
    assert (r["start_date"], r["end_date"]) == want


def test_card_schema_kinds():
    variants = cp.card_schema()["properties"]["steps"]["items"]["anyOf"]
    assert [v["properties"]["kind"]["const"] for v in variants] == ["concept", "quiz", "causal_order", "chart", "judgement"]


# --- 에이전트 루프 (가짜 Claude) ---

def resp(stop, *blocks):
    return SimpleNamespace(stop_reason=stop, content=list(blocks), _request_id=f"req_{len(blocks)}_{stop}",
                           usage=SimpleNamespace(input_tokens=1000, output_tokens=100,
                                                 cache_creation_input_tokens=0, cache_read_input_tokens=0))


def submit(card, n=0):
    return SimpleNamespace(type="tool_use", id=f"tu_submit_{n}", name="submit_card", input=copy.deepcopy(card))


def tool_use(name, **args):
    return SimpleNamespace(type="tool_use", id=f"tu_{name}", name=name, input=args)


def fake(monkeypatch, replies):
    calls = []

    def create(module, **params):
        calls.append(copy.deepcopy(params["messages"]))
        return replies.pop(0)

    monkeypatch.setattr(cp, "create", create)
    return calls


def test_loop_tool_then_answer(offline, monkeypatch):
    card = good_card(offline)
    calls = fake(monkeypatch, [
        resp("tool_use", tool_use("find_concept_path", start_concept="rate_hold",
                                  end_concept="growth_valuation", change="up")),
        resp("tool_use", submit(card)),
    ])
    r = cp.compose(SOURCE, CLS2, date(2026, 11, 2), save=False)
    assert r.errors == [] and r.card == card and r.calls == 2 and r.repairs == 0
    # 두 번째 호출에 도구 결과가 tool_result 로 들어갔다
    tool_result = calls[1][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["is_error"] is False
    assert json.loads(tool_result["content"])["results"][0]["direction"] == "down"
    # 비용: Sonnet 입력 1000 × $2/1M + 출력 100 × $10/1M = 0.003 × 2회
    assert r.cost_usd == pytest.approx(0.006)


def test_repair_then_pass(offline, monkeypatch):
    bad, good = good_card(offline), good_card(offline)
    bad["steps"][3]["chart_check"]["value"] = "2.5"
    calls = fake(monkeypatch, [resp("tool_use", submit(bad, 0)), resp("tool_use", submit(good, 1))])
    r = cp.compose(SOURCE, CLS2, date(2026, 11, 2), save=False)
    assert r.errors == [] and r.repairs == 1
    (feedback,) = calls[1][-1]["content"]  # 실패 이유는 submit_card 의 tool_result 로 돌아간다
    assert feedback["tool_use_id"] == "tu_submit_0" and feedback["is_error"] is True
    assert "코드가 계산한 값은 3.0" in feedback["content"]


def test_gives_up_after_max_repairs(offline, monkeypatch):
    bad = good_card(offline)
    bad["slides"][0]["body"] = "지금 사세요."
    fake(monkeypatch, [resp("tool_use", submit(bad, i)) for i in range(cp.MAX_REPAIRS + 1)])
    r = cp.compose(SOURCE, CLS2, date(2026, 11, 2), save=False)
    assert r.repairs == cp.MAX_REPAIRS and r.card_id is None
    assert any("사세요" in e for e in r.errors)


def test_call_cap(offline, monkeypatch):
    monkeypatch.setattr(cp, "MAX_CALLS", 3)
    fake(monkeypatch, [resp("tool_use", tool_use("search_event_dates", concept_id="volume_spike", limit=1))
                       for _ in range(3)])
    r = cp.compose(SOURCE, CLS2, date(2026, 11, 2), save=False)
    assert r.calls == 3 and r.card is None and "호출 상한" in r.errors[0]


def test_review_hook(offline, monkeypatch):
    card = good_card(offline)
    fake(monkeypatch, [resp("tool_use", submit(card, 0)), resp("tool_use", submit(card, 1))])
    seen = []

    def review(c):
        seen.append(c)
        return ["정답이 두 개로 읽혀요"] if len(seen) == 1 else []

    r = cp.compose(SOURCE, CLS2, date(2026, 11, 2), save=False, review=review)
    assert r.errors == [] and r.repairs == 1 and len(seen) == 2


def test_text_answer_is_nudged_to_submit(offline, monkeypatch):
    card = good_card(offline)
    plain = SimpleNamespace(type="text", text="카드를 만들었어요")
    calls = fake(monkeypatch, [resp("end_turn", plain), resp("tool_use", submit(card))])
    r = cp.compose(SOURCE, CLS2, date(2026, 11, 2), save=False)
    assert r.errors == [] and r.calls == 2
    assert "submit_card" in calls[1][-1]["content"]


def test_tool_and_submit_same_turn(offline, monkeypatch):
    bad, good = good_card(offline), good_card(offline)
    bad["slides"].pop()
    other = tool_use("search_event_dates", concept_id="volume_spike", limit=1)
    calls = fake(monkeypatch, [resp("tool_use", other, submit(bad, 0)), resp("tool_use", submit(good, 1))])
    r = cp.compose(SOURCE, CLS2, date(2026, 11, 2), save=False)
    assert r.errors == [] and r.repairs == 1
    ids = [b["tool_use_id"] for b in calls[1][-1]["content"]]  # 같은 턴의 다른 도구 결과도 함께 돌려준다
    assert ids == ["tu_search_event_dates", "tu_submit_0"]


@pytest.mark.parametrize("break_it, expect", [
    (lambda c: c.pop("key_facts"), "card.key_facts: 빠졌어요"),
    (lambda c: c["steps"][1].update(answer_index="2"), "card.steps[1].answer_index: integer"),
    (lambda c: c["steps"][1].update(kind="essay"), "알 수 없는 kind"),
    (lambda c: c["steps"][3]["chart_check"].update(metric="sharpe"), "중 하나여야"),
])
def test_shape_errors(offline, ids, break_it, expect):
    card = good_card(offline)
    break_it(card)
    errors = cp.validate_card(card, 2, ids, CTX)
    assert any(expect in e for e in errors), errors


# --- 정답 보기에 확인한 값이 있는지 (표기가 달라도 숫자로 비교) ---

@pytest.mark.parametrize("option, metric, expected, ok", [
    ("3배", "volume_ratio", 3.0, True),
    ("평균의 3.0배", "volume_ratio", 3.0, True),
    ("약 3배", "volume_ratio", 3.04, True),        # 정수 표기는 ±0.5 안이면 같은 값
    ("2배", "volume_ratio", 3.0, False),
    ("약 -16.48%", "return_pct", -16.48, True),
    ("약 +16.48%", "return_pct", -16.48, False),   # 부호가 다르면 다른 값
    ("약 -16.5%", "return_pct", -16.48, True),     # 소수 한 자리 표기 ±0.05
    ("약 -16.4%", "return_pct", -16.48, False),
    ("RSI 1,234.5", "rsi", 1234.5, True),
    ("2026-10-30", "top_volume_date", "2026-10-30", True),
    ("10월 30일", "top_volume_date", "2026-10-30", True),
    ("10/30(목)", "top_volume_date", "2026-10-30", True),
    ("2025-10-30", "top_volume_date", "2026-10-30", False),  # 연도가 적혀 있으면 연도도 본다
    ("10월 29일", "top_volume_date", "2026-10-30", False),
    ("2026-10-30 기준 -10%", "return_pct", -10.0, True),      # 날짜 속 '-10' 은 숫자로 읽지 않는다
    ("2026-10-30", "return_pct", -10.0, False),
])
def test_option_matches(option, metric, expected, ok):
    assert cp.option_matches(option, metric, expected) is ok


# --- ETF 변화율은 코드가 문구로 바꿔서 넘긴다 (소수 0.053097 = +5.3%, NULL = 신규 편입) ---

@pytest.mark.parametrize("trend, day, base, want_trend, want_day", [
    (0.053097, -0.012, date(2026, 9, 30), "9/30 대비 +5.3%", "-1.2%"),
    (0.0, 0.0, date(2026, 9, 30), "9/30 대비 +0.0%", "+0.0%"),
    (None, None, date(2026, 9, 30), "9/30 이후 신규 편입", "전 거래일에 없던 종목 (신규)"),
    (None, 0.01, None, "추세 기준일 없음", "+1.0%"),
])
def test_etf_row_text(trend, day, base, want_trend, want_day):
    from decimal import Decimal

    row = cp.etf_row_text("426030", date(2026, 10, 30), Decimal("12345"), trend, day, base)
    assert row["분기 말 대비 추세"] == want_trend
    assert row["전 거래일 대비"] == want_day
    assert row["보유 수량"] == "12,345주" and row["기준일"] == "2026-10-30"
