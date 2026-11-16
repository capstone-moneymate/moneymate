"""scripts/run_reasons.py (탭 2 카드 ②③ 분기 생성). DB·LLM 없이 가짜 함수로 흐름과 문장을 본다."""
from datetime import date

import pytest

from generate import reasons, stock_now
from generate.reasons import Evidence, Reason, ReasonsResult
from scripts import run_reasons as rr

BASE = date(2026, 9, 30)


def _row(filer, etf, big, etf_pct, d, change_type="increase"):
    return {"ticker": "NVDA", "filer_key": filer, "big_chg_pct": big, "etf_code": etf, "etf_trend_chg_pct": etf_pct,
            "direction": d, "change_type": change_type, "issuer_name": "NVIDIA CORP"}


ROWS = [_row("druckenmiller", "426030", 0.24, 0.15, "same"), _row("druckenmiller", "0015B0", 0.24, -0.163, "diff"),
        _row("thiel", "426030", None, 0.15, "same", "new"), _row("thiel", "0015B0", None, -0.163, "diff", "new")]


@pytest.mark.parametrize("v,text", [(0.24, "+24%"), (-0.16318, "-16.3%"), (0.0, "0%"), (None, None), (1.0, "+100%")])
def test_pct_text(v, text):
    assert rr.pct_text(v) == text


def test_facts_once_per_filer_and_etf():
    # 큰손 2명, ETF 2개 → 4문장. 쌍마다 반복하지 않는다. 새로 담음은 변화율 대신 말로
    assert rr.facts_for(ROWS, BASE) == [
        "드러켄밀러의 회사 09/30 기준 +24%",
        "TIME 09/30 대비 +15%",
        "KoAct 09/30 대비 -16.3%",
        "틸의 회사 09/30 기준 새로 담음",
    ]


class Conn:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def _fake(monkeypatch, *, evidence=1, reasons_out=None, prices_fail=False):
    calls = {}

    def fill(conn, ticker, period):
        if prices_fail:
            raise ConnectionError("가격 서버")
        calls["prices"] = (ticker, period)
        return 0

    monkeypatch.setattr(rr, "fill_prices", fill)
    ev = [Evidence(i, i, "2026-09-12", "t", "N", "u") for i in range(1, evidence + 1)]
    monkeypatch.setattr(reasons, "load_evidence", lambda t, p: ev)
    reason = Reason("AI 투자", "본문", "gpu_demand", "semi_earnings", ["gpu_demand", "semi_earnings"], "up", ev[:1])
    out = reasons_out if reasons_out is not None else ReasonsResult("왜 방향이 다를까요?", [reason], calls=1)

    def gen(stock, direction, change, period, facts, evid):
        calls["generate"] = (stock, direction, change, period, facts, len(evid))
        return out

    monkeypatch.setattr(reasons, "generate", gen)
    monkeypatch.setattr(stock_now, "generate",
                        lambda stock, period, rs_: calls.setdefault("now", rs_) and stock_now.StockNow("2026-09-30",
                                                                                                         calls=1))

    def save(conn, period, ticker, d, c, result, now_view, info):
        calls["save"] = (ticker, d, c, bool(result.reasons), now_view)
        return "published" if result.reasons else "rejected"

    monkeypatch.setattr(reasons, "save", save)
    return calls


def test_run_one_generates_and_saves(monkeypatch):
    calls = _fake(monkeypatch)
    conn = Conn()
    run = rr.run_one(conn, "NVDA", ROWS, BASE, llm=True)
    # diff 가 있으니 diff, 큰손: 드러켄밀러 +0.24, 틸 새로 담음 → up
    assert (run.direction, run.change, run.status, run.calls, run.evidence) == ("diff", "up", "published", 2, 1)
    stock, d, c, period, facts, n = calls["generate"]
    assert stock == {"ticker": "NVDA", "name": "NVIDIA CORP"} and (d, c, period, n) == ("diff", "up", BASE, 1)
    assert "TIME 09/30 대비 +15%" in facts
    assert calls["save"][:4] == ("NVDA", "diff", "up", True) and calls["save"][4]["base_date"] == "2026-09-30"
    assert conn.commits == 1  # 종목마다 저장
    assert calls["prices"] == ("NVDA", BASE)  # 카드 ③ 전에 미국 가격을 받는다


def test_run_one_keeps_going_when_prices_fail(monkeypatch):
    calls = _fake(monkeypatch, prices_fail=True)
    run = rr.run_one(Conn(), "NVDA", ROWS, BASE, llm=True)
    assert run.status == "published" and "now" in calls  # 가격 없이도 카드 ③은 만든다


def test_run_one_without_reasons_saves_rejected_without_card3(monkeypatch):
    calls = _fake(monkeypatch, evidence=0, reasons_out=ReasonsResult("왜 방향이 다를까요?", [], ["근거 없음"]))
    run = rr.run_one(Conn(), "NVDA", ROWS, BASE, llm=True)
    assert run.status == "rejected" and "now" not in calls and calls["save"][4] is None


def test_run_one_no_llm_only_counts(monkeypatch):
    calls = _fake(monkeypatch, evidence=3)
    run = rr.run_one(Conn(), "NVDA", ROWS, BASE, llm=False)
    assert (run.direction, run.change, run.evidence, run.status) == ("diff", "up", 3, None)
    assert "generate" not in calls and "save" not in calls


def test_run_one_without_change_values_is_skipped(monkeypatch):
    calls = _fake(monkeypatch)
    rows = [_row("thiel", "426030", None, None, "none")]
    run = rr.run_one(Conn(), "NVDA", rows, BASE, llm=True)
    assert run.error and run.status is None and calls == {}
