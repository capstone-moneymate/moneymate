"""stock_now.py (카드 ③ 지금은) 와 reasons.save. 네트워크·DB 없이 손계산 값으로 본다."""
import json
from datetime import date
from types import SimpleNamespace

import pytest

from generate import reasons as rs
from generate import stock_now as sn
from generate.classify import Concept
from generate.reasons import Evidence, Reason, ReasonsResult

BASE = date(2026, 9, 30)
STOCK = {"ticker": "NVDA", "name": "엔비디아"}
CONCEPTS = [Concept("ai_investment", "AI 데이터센터 투자", "AI·반도체", []),
            Concept("gpu_demand", "AI 반도체 수요", "AI·반도체", []),
            Concept("semi_earnings", "반도체 기업 실적", "AI·반도체", [])]
EV = Evidence(1, 10, "2026-09-12", "테스트 8-K Item 2.02", "NVIDIA", "https://example.com/1")
REASONS = [
    Reason("AI 투자 확대", "데이터센터 투자가 늘었을 수 있어요.", "ai_investment", "semi_earnings",
           ["ai_investment", "gpu_demand", "semi_earnings"], "up", [EV]),
    Reason("실적 기대", "실적이 좋아졌을 수 있어요.", "gpu_demand", "semi_earnings",
           ["gpu_demand", "semi_earnings"], "up", [EV]),
]
# 9/30 은 휴장이라 가정: 기준일 이하 마지막 종가는 9/29 100, 최근 11/14 112.5 → +12.5%
PRICES = [(date(2026, 9, 26), 98.0), (date(2026, 9, 29), 100.0), (date(2026, 10, 1), 103.0), (date(2026, 11, 14), 112.5)]
LATER = [sn.LaterSource(55, "2026-11-12", "NVIDIA 8-K Item 2.02", "https://example.com/55",
                        {"매출액 전년동기대비(%)": 62.0, "영업이익 전년동기대비 방향": "증가"})]


def test_price_since_uses_last_close_on_or_before_base():
    p = sn.price_since(PRICES, BASE)
    assert (p.from_date, p.from_close, p.to_date, p.to_close) == ("2026-09-29", 100.0, "2026-11-14", 112.5)
    assert p.return_pct == 12.5  # (112.5 / 100 - 1) × 100


def test_price_since_needs_both_sides():
    assert sn.price_since(PRICES[:2], BASE) is None  # 기준일 뒤 거래일 없음
    assert sn.price_since(PRICES[2:], BASE) is None  # 기준일 이전 종가 없음
    assert sn.price_since([], BASE) is None


def test_price_since_rounds_to_two_places():
    # 3 → 3.5: 16.666… → 16.67
    assert sn.price_since([(date(2026, 9, 30), 3.0), (date(2026, 10, 2), 3.5)], BASE).return_pct == 16.67
    # 종가도 둘째 자리 (yfinance 원본 1154.2900390625). 수익률은 원본으로: 778.309997558594 / 1154.2900390625 - 1 = -32.57%
    p = sn.price_since([(date(2026, 6, 30), 1154.2900390625), (date(2026, 11, 13), 778.309997558594)], date(2026, 6, 30))
    assert (p.from_close, p.to_close, p.return_pct) == (1154.29, 778.31, -32.57)


def test_linked_concepts_follow_reason_paths_once():
    linked = sn.linked_concepts(REASONS, {"gpu_demand", "rate_hold"}, CONCEPTS)
    # gpu_demand 는 두 이유 경로에 다 있지만 처음 이유에만 붙는다. 경로에 없는 rate_hold 는 빠진다
    assert [(c.concept_id, c.name, c.reason_title) for c in linked] == [("gpu_demand", "AI 반도체 수요", "AI 투자 확대")]
    assert sn.linked_concepts(REASONS, set(), CONCEPTS) == []


def test_trim_numbers_keeps_rates_and_directions_first():
    # DB 가 돌려주는 순서(키 길이 순)를 흉내: 금액·전기대비가 앞에 와도 전년동기 증감률·방향이 남아야 한다
    numbers = {"단위": "백만원", "매출액": 535934, "영업이익": 101787, "당기순이익": 25482,
               "매출액 전년동기": 372839, "영업이익 전기대비(%)": 61.8, "매출액 전기대비 방향": "증가",
               "매출액 전년동기대비(%)": 43.7, "영업이익 전년동기대비(%)": 721.6,
               "영업이익 전년동기대비 방향": "증가", "당기순이익 전년동기대비 방향": "증가"}
    out = sn.trim_numbers(numbers)
    assert len(out) == sn.MAX_NUMBERS
    assert list(out)[:4] == ["매출액 전년동기대비(%)", "영업이익 전년동기대비(%)",
                             "영업이익 전년동기대비 방향", "당기순이익 전년동기대비 방향"]
    assert "영업이익 전기대비(%)" not in out and "매출액 전기대비 방향" not in out  # 전기대비는 맨 뒤라 잘림
    # 시설투자·공급계약 비율도 앞으로
    assert list(sn.trim_numbers({"투자목적": "증설", "투자금액(원)": 1, "자기자본대비(%)": 18.3}))[0] == "자기자본대비(%)"
    assert sn.trim_numbers(None) == {}


PAYLOAD = sn.facts_payload(STOCK, sn.StockNow("2026-09-30", sn.price_since(PRICES, BASE), LATER))


@pytest.mark.parametrize("text", [
    "9월 29일 100달러였던 주가는 11월 14일 112.5달러로 12.5% 올랐어요.",
    "11월 12일 실적 공시에서 매출액이 전년 동기보다 62% 늘었어요.",
    "주가는 기준일보다 12.50% 높아요.",  # 끝자리 0 은 같은 숫자로 본다
])
def test_check_text_accepts_numbers_from_facts(text):
    assert sn.check_text(text, PAYLOAD) == []


def test_check_text_rejects_new_numbers_banned_and_empty():
    assert "입력에 없는 숫자" in sn.check_text("주가는 15% 올랐어요.", PAYLOAD)[0]
    assert any("쓰면 안 되는 표현" in e for e in sn.check_text("앞으로 오를 것이다.", PAYLOAD))
    assert sn.check_text("  ", PAYLOAD) == ["문장이 비어 있어요"]
    assert any("줄여" in e for e in sn.check_text("가" * 301, PAYLOAD))


def fake_create(monkeypatch, *texts, stop="end_turn"):
    queue, calls = list(texts), []

    def create(module, **kwargs):
        calls.append({"module": module, **kwargs, "messages": list(kwargs["messages"])})
        body = json.dumps({"text": queue.pop(0)}, ensure_ascii=False)
        return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=body)])

    monkeypatch.setattr(sn, "create", create)
    return calls


def build(monkeypatch, *texts, prices=PRICES, later=LATER, today_ids=frozenset({"gpu_demand"}), llm=True):
    calls = fake_create(monkeypatch, *texts)
    return sn.build_now(STOCK, BASE, REASONS, prices, later, set(today_ids), CONCEPTS, llm), calls


def test_build_now_writes_text_with_haiku(monkeypatch):
    now, calls = build(monkeypatch, "기준일 뒤 주가는 12.5% 올랐어요. 오늘 배운 AI 반도체 수요가 첫 이유와 이어져요.")
    assert now.text.startswith("기준일 뒤") and now.errors == [] and now.calls == 1
    assert calls[0]["module"] == "stock_now" and calls[0]["model"] == sn.HAIKU
    sent = calls[0]["messages"][0]["content"]
    assert sent.startswith("<facts>") and '"return_pct": 12.5' in sent and "AI 반도체 수요" in sent
    out = now.to_json()
    assert set(out) == {"base_date", "price", "later_sources", "linked", "text", "errors"}
    assert out["price"]["return_pct"] == 12.5 and out["later_sources"][0]["source_id"] == 55


def test_build_now_repairs_once_then_gives_up_with_facts(monkeypatch):
    # 20·47 은 입력 어디에도 없다 (기준일 9/30 의 30 은 입력에 있어서 쓰지 않음)
    now, calls = build(monkeypatch, "주가는 20% 올랐어요.", "주가는 47% 올랐어요.")
    assert now.text is None and now.calls == 2
    assert "입력에 없는 숫자" in now.errors[0]
    # 두 번째 호출에는 고칠 이유가 붙는다. 사실은 그대로 남는다
    assert "다시 써 주세요" in calls[1]["messages"][-1]["content"]
    assert now.price.return_pct == 12.5 and now.linked[0].concept_id == "gpu_demand"


def test_build_now_without_data_skips_llm(monkeypatch):
    now, calls = build(monkeypatch, prices=[], later=[])
    assert calls == [] and now.text is None and "이후 주가와 자료가 없어요" in now.errors[0]


def test_build_now_no_llm(monkeypatch):
    now, calls = build(monkeypatch, llm=False)
    assert calls == [] and now.text is None and now.errors == [] and now.price.return_pct == 12.5


def test_cut_off_response_raises(monkeypatch):
    fake_create(monkeypatch, "x", stop="max_tokens")
    with pytest.raises(RuntimeError):
        sn.build_now(STOCK, BASE, REASONS, PRICES, LATER, set(), CONCEPTS)


# --- reasons.save (A 의 004_stock_reasons, P19) ---

class FakeConn:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))


def test_save_published_with_now_view():
    conn = FakeConn()
    result = ReasonsResult("왜 다 늘렸을까요?", REASONS, calls=1)
    assert rs.save(conn, BASE, "NVDA", "same", "up", result, {"text": "지금은"}, {"model": "sonnet"}) == "published"
    sql, params = conn.calls[0]
    assert "INSERT INTO stock_reasons" in sql and "now_view" in sql and "updated_at = now()" in sql
    assert params[:5] == (BASE, "NVDA", "same", "up", "왜 다 늘렸을까요?")
    saved = params[5].obj
    assert saved[0]["path"] == ["ai_investment", "gpu_demand", "semi_earnings"]
    assert saved[0]["evidence"][0]["source_id"] == 10
    assert "numbers" not in saved[0]["evidence"][0]  # 근거 numbers 는 프롬프트용이라 저장하지 않는다
    assert params[6].obj == {"text": "지금은"}
    assert params[7] == "published" and params[8].obj == {"calls": 1, "model": "sonnet"}


def test_save_direction_warnings_as_pending():
    # 큰손과 반대 방향 이유가 있으면 pending: 화면(서버는 published 만)에 안 나가고 사람이 본다 (B·C 합의)
    conn = FakeConn()
    result = ReasonsResult("왜 다 늘렸을까요?", REASONS, calls=1, warnings=["이유 1: 반대"])
    assert rs.save(conn, BASE, "NVDA", "same", "up", result, None) == "pending"
    assert conn.calls[0][1][7] == "pending"
    assert conn.calls[0][1][8].obj == {"calls": 1, "warnings": ["이유 1: 반대"]}
    assert conn.calls[0][1][5].obj[0]["change"] == "up"  # 시작 개념 변화도 저장


def test_save_rejected_keeps_errors_and_null_now_view():
    conn = FakeConn()
    result = ReasonsResult("왜 다 늘렸을까요?", [], ["근거 자료가 없어요"])
    assert rs.save(conn, BASE, "NVDA", "same", "up", result, None) == "rejected"
    params = conn.calls[0][1]
    assert params[5].obj == [] and params[6] is None
    assert params[8].obj == {"calls": 0, "errors": ["근거 자료가 없어요"]}


def _pair(filer, big, etf, d, change_type=None):
    # 003 에서 etf_trend_adj_pct → etf_trend_chg_pct. 변화율은 P2 비율이지만 부호만 보므로 값 크기는 상관없다
    return {"ticker": "NVDA", "filer_key": filer, "big_chg_pct": big, "etf_trend_chg_pct": etf, "direction": d,
            "change_type": change_type}


def test_stock_direction_rules():
    # 큰손 2명 × ETF 2개. 한 쌍이라도 diff 면 diff
    rows = [_pair("a", 24.0, 15.0, "same"), _pair("a", 24.0, -8.0, "diff"),
            _pair("b", 10.0, 15.0, "same"), _pair("b", 10.0, -8.0, "diff")]
    assert rs.stock_direction(rows) == ("diff", "up")
    # diff 없이 same 이 있으면 same. 큰손 부호 2 대 1 → down (큰손마다 한 번만 센다)
    rows = [_pair("a", -5.0, -3.0, "same"), _pair("a", -5.0, None, "none"),
            _pair("b", -7.0, -3.0, "same"), _pair("c", 6.0, -3.0, "none")]
    assert rs.stock_direction(rows) == ("same", "down")
    # 1 대 1 이면 합의 부호: +3 + (-5) = -2 → down
    assert rs.stock_direction([_pair("a", 3.0, 1.0, "none"), _pair("b", -5.0, 1.0, "none")]) == ("none", "down")
    # 큰손 값이 없으면 ETF 합의 부호
    assert rs.stock_direction([_pair("a", None, 4.0, "none"), _pair("b", 0, -1.0, "none")]) == ("none", "up")
    # 새로 담음은 변화율이 NULL(P2)이어도 +1 로 센다: 새로 담음 1 + 줄임(-0.1) 1 → 1 대 1, 합 +0.9 → up
    rows = [_pair("a", None, -0.2, "diff", "new"), _pair("b", -0.1, -0.2, "same", "decrease")]
    assert rs.stock_direction(rows) == ("diff", "up")
    # 모두 정리는 -1 (P12) → down
    assert rs.stock_direction([_pair("a", -1.0, -0.3, "same", "exit")]) == ("same", "down")


def test_stock_direction_needs_values():
    with pytest.raises(ValueError):
        rs.stock_direction([])
    with pytest.raises(ValueError):
        rs.stock_direction([_pair("a", None, None, "none")])
