"""concepts/regime.py (#174) 와 국면을 받는 검증기·출제 도구. FRED 는 부르지 않는다 (conftest 가 막음, 여기선 가짜 표)."""
import json
from datetime import date

import pytest

from concepts import regime as rg
from generate import tools
from validate.validators import verify

# 2024년 실제 값 (FRED SAHMREALTIME, 2026-11-19 받은 값): 8월 0.57 로 0.5 를 넘었다가 10월 0.43
SERIES_2024 = [(date(2024, 7, 1), 0.53), (date(2024, 8, 1), 0.57), (date(2024, 9, 1), 0.50), (date(2024, 10, 1), 0.43)]


@pytest.mark.parametrize("value, want", [
    (0.00, "normal"), (0.49, "normal"),
    (0.50, "recession"),                    # 0.5 이상이면 침체 (경계 포함)
    (0.57, "recession"),
    (0.1 + 0.2 + 0.2, "recession"),         # 0.5000000000000001 같은 float 도 둘째 자리로 맞춘다
    (-0.07, "normal"),                      # 실업률이 최저보다 낮으면 음수
])
def test_regime_of_threshold(value, want):
    assert rg.regime_of(value) == want


def test_uses_only_months_before_the_date():
    # 10월 값은 11월 초에 나오므로 10/15 카드는 9월 값(0.50 → 침체), 11/1 카드부터 10월 값(0.43 → 평상시)
    assert rg.latest_before_month(SERIES_2024, date(2024, 10, 15)) == (date(2024, 9, 1), 0.50)
    assert rg.latest_before_month(SERIES_2024, date(2024, 11, 1)) == (date(2024, 10, 1), 0.43)
    assert rg.latest_before_month(SERIES_2024, date(2024, 7, 31)) is None


def test_current_regime_with_values():
    r = rg.current_regime(date(2024, 9, 15), fetch=lambda d: SERIES_2024)
    assert r == rg.Regime("recession", 0.57, "2024-08-01", "FRED SAHMREALTIME")
    assert r.to_json() == {"name": "recession", "sahm": 0.57, "observed": "2024-08-01", "source": "FRED SAHMREALTIME"}
    assert rg.current_regime(date(2024, 11, 19), fetch=lambda d: SERIES_2024).name == "normal"


def test_fetch_failure_or_no_value_falls_back_to_normal():
    def down(d):
        raise ConnectionError("no network")

    r = rg.current_regime(date(2026, 11, 19), fetch=down)
    assert r.name == "normal" and r.sahm is None and "받지 못해 평상시로 둠: ConnectionError" in r.source
    r = rg.current_regime(date(2024, 7, 15), fetch=lambda d: SERIES_2024)
    assert r.name == "normal" and "앞 달 값이 없어" in r.source


def test_month_cache_calls_fred_once(monkeypatch):
    calls = []
    monkeypatch.setattr(rg, "fetch_sahm", lambda d: calls.append(d) or SERIES_2024)
    rg.regime_for_month.cache_clear()
    assert rg.regime_for_month(2024, 9).name == "recession"
    assert rg.regime_for_month(2024, 9).name == "recession"
    assert len(calls) == 1


def test_prompt_note_only_in_recession():
    assert rg.prompt_note(rg.Regime("normal", 0.0, "2026-10-01")) is None
    note = rg.prompt_note(rg.Regime("recession", 0.57, "2024-08-01"))
    assert "경기 침체 국면" in note and "2024-08 = 0.57" in note


# ---- 검증기·출제 도구가 국면을 쓴다 (실제 사전: 경기 침체에서는 국채 금리 → 성장주 가치평가가 반대) ----

SOURCE = "연준이 기준금리를 인하했다."
QUIZ = {"start_concept": "rate_cut", "change": "up", "end_concept": "growth_valuation",
        "answer_order": ["rate_cut", "bond_yield", "growth_valuation"], "direction": "up", "evidence_quote": SOURCE}


def test_verify_by_regime():
    # 손계산: 인하 → 국채 금리 (-1), 국채 금리 → 성장주 평상시 (-1) → (+1) ▲ / 경기 침체 (+1) → (-1) ▼
    assert verify(QUIZ, SOURCE).errors == []                              # 국면을 안 주면 평상시 (예전과 같음)
    errors = verify(QUIZ, SOURCE, regime="recession").errors
    assert errors == ["오르내림 방향이 개념 사전과 다름 (사전: 하락 압력, 퀴즈: 상승 압력)"]
    assert verify({**QUIZ, "direction": "down"}, SOURCE, regime="recession").errors == []


def test_tools_use_context_regime():
    args = {"start_concept": "rate_cut", "end_concept": "growth_valuation", "change": "up"}
    normal, _ = tools.run_tool("find_concept_path", args, tools.ToolContext())
    rec, _ = tools.run_tool("find_concept_path", args, tools.ToolContext(regime="recession"))
    assert json.loads(normal)["regime"] == "normal" and json.loads(normal)["results"][0]["direction"] == "up"
    assert json.loads(rec)["regime"] == "recession" and json.loads(rec)["results"][0]["direction"] == "down"
    out, _ = tools.run_tool("validate_causal_order", {"quiz": QUIZ}, tools.ToolContext(SOURCE, regime="recession"))
    assert json.loads(out)["passed"] is False
