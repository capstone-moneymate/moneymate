"""generate/tools.py 테스트. DB 는 부르지 않는다 (load_prices 를 가짜 표로 바꾼다). 손계산이 정답."""
import json
from datetime import date, timedelta

import pandas as pd
import pytest

from generate import tools


# --- 계산 (손계산) ---

def test_rsi_hand_calc():
    # 종가 10, 11, 10, 12, 13 / period 2 → 변화 +1, -1, +2, +1
    # 첫 평균: 이익 (1+0)/2 = 0.5, 손실 (0+1)/2 = 0.5
    # +2: 이익 (0.5×1+2)/2 = 1.25, 손실 (0.5×1+0)/2 = 0.25
    # +1: 이익 (1.25+1)/2 = 1.125, 손실 0.25/2 = 0.125 → RS 9 → RSI 100 - 100/10 = 90
    assert tools.wilder_rsi([10, 11, 10, 12, 13], period=2) == 90.0


def test_rsi_after_first_average():
    # 위에서 +2 까지만: RS = 1.25/0.25 = 5 → 100 - 100/6 = 83.33
    assert tools.wilder_rsi([10, 11, 10, 12], period=2) == 83.33


def test_rsi_no_loss_is_100():
    assert tools.wilder_rsi([1, 2, 3, 4], period=2) == 100.0


def test_rsi_too_short():
    with pytest.raises(tools.ToolError):
        tools.wilder_rsi([1, 2], period=2)


def test_pct_return():
    assert tools.pct_return(200, 210) == 5.0
    assert tools.pct_return(80, 79) == -1.25


def test_volume_ratio():
    # 앞 3일 평균 (100+200+300)/3 = 200, 오늘 500 → 2.5배
    assert tools.volume_ratio([100, 200, 300, 500]) == 2.5


def test_top_volume_tie_earlier_first():
    df = pd.DataFrame({"market_date": [date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5)],
                       "volume": [300, 500, 500]})
    assert tools.top_volume_days(df, 2) == [{"date": "2026-10-02", "volume": 500},
                                            {"date": "2026-10-05", "volume": 500}]


# --- 도구 (가짜 가격표) ---

@pytest.fixture
def fake_prices(monkeypatch, tmp_path):
    """2026-09-01 부터 평일 300일. 종가 100,101,...  거래량은 마지막 날만 3000, 나머지 1000."""
    days, d = [], date(2026, 9, 1)
    while len(days) < 300:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    full = pd.DataFrame({"market_date": days, "close": [100.0 + i for i in range(300)],
                         "volume": [1000] * 299 + [3000]})

    def load(ticker, end, n):
        if ticker != "005930":
            raise tools.ToolError(f"{ticker} 의 {end} 이전 가격이 없어요")
        df = full[full["market_date"] <= end].tail(n)
        return df.reset_index(drop=True)

    monkeypatch.setattr(tools, "load_prices", load)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "tool_calls.jsonl")
    return full


def run(name, **args):
    content, is_error = tools.run_tool(name, args)
    return (content if is_error else json.loads(content)), is_error


def test_calc_return_tool(fake_prices):
    first, last = fake_prices.iloc[0], fake_prices.iloc[4]
    out, err = run("calc_return", ticker="005930", start_date=str(first.market_date), end_date=str(last.market_date))
    # 100 → 104 = +4%
    assert not err and out["return_pct"] == 4.0


def test_volume_stats_tool(fake_prices):
    last = fake_prices.iloc[-1].market_date
    out, err = run("volume_stats", ticker="005930", date=str(last), days=3)
    # 직전 252일 평균 1000, 오늘 3000 → 3배
    assert not err
    assert out["ratio_to_avg"] == 3.0 and out["avg_days"] == 252
    assert out["window"] == [str(d) for d in fake_prices["market_date"].iloc[-3:]]
    assert out["window_top"][0] == {"date": str(last), "volume": 3000}


def test_volume_stats_not_trading_day(fake_prices):
    out, err = run("volume_stats", ticker="005930", date="2026-09-05", days=3)  # 토요일
    assert err and "거래일이 아니에요" in out


def test_calc_rsi_rising_is_100(fake_prices):
    out, err = run("calc_rsi", ticker="005930", date=str(fake_prices.iloc[-1].market_date), period=14)
    assert not err and out["rsi"] == 100.0


def test_volume_stats_days_range(fake_prices):
    out, err = run("volume_stats", ticker="005930", date=str(fake_prices.iloc[-1].market_date), days=21)
    assert err and "1~20" in out


# --- 차트 정답 검증 (가짜 가격표: 종가 100,101,..., 거래량은 마지막 날만 3000) ---

def chart(fake_prices, metric, value, start=0, end=4):
    s = str(fake_prices.iloc[start].market_date) if start is not None else None
    e = str(fake_prices.iloc[end].market_date)
    return run("validate_chart_answer", metric=metric, ticker="005930", start_date=s, end_date=e, value=value)


def test_chart_return(fake_prices):
    out, err = chart(fake_prices, "return_pct", "4.0%")  # 100 → 104
    assert not err and out["passed"]
    out, err = chart(fake_prices, "return_pct", "4.5")
    assert not err and not out["passed"] and out["expected"] == 4.0 and "4.0" in out["error"]


def test_chart_volume_ratio_and_top_date(fake_prices):
    out, err = chart(fake_prices, "volume_ratio", "3배", start=None, end=-1)
    assert not err and out["passed"]
    last = str(fake_prices.iloc[-1].market_date)
    out, err = chart(fake_prices, "top_volume_date", last, start=-3, end=-1)
    assert not err and out["passed"]
    out, err = chart(fake_prices, "top_volume_date", str(fake_prices.iloc[-2].market_date), start=-3, end=-1)
    assert not err and not out["passed"] and out["expected"] == last


def test_chart_rsi(fake_prices):
    out, err = chart(fake_prices, "rsi", "100", start=None, end=-1)  # 계속 올라 손실 0
    assert not err and out["passed"]


def test_chart_bad_inputs(fake_prices):
    out, err = chart(fake_prices, "return_pct", "4", start=None)
    assert err and "start_date" in out
    out, err = chart(fake_prices, "return_pct", "많이 올랐다")
    assert err and "숫자" in out


def test_errors_are_returned_and_logged(fake_prices, tmp_path):
    out, err = run("calc_return", ticker="NVDA", start_date="2026-09-01", end_date="2026-09-10")
    assert err and "NVDA" in out
    out, err = run("calc_return", ticker="005930", start_date="9월 1일", end_date="2026-09-10")
    assert err and "YYYY-MM-DD" in out
    out, err = run("no_such_tool")
    assert err

    rows = [json.loads(line) for line in (tmp_path / "tool_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["ok"] for r in rows] == [False, False, False]
    assert rows[0]["tool"] == "calc_return" and rows[0]["input"]["ticker"] == "NVDA"


# --- 개념 경로·이벤트 날짜 (db/seeds) ---

def test_find_concept_path_rate_hold(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "t.jsonl")
    out, err = run("find_concept_path", start_concept="rate_hold", end_concept="growth_valuation", change="up")
    assert not err
    (res,) = out["results"]
    assert res["direction"] == "down"
    assert ["rate_hold", "growth_valuation"] in [p["concept_ids"] for p in res["paths"]]


def test_find_concept_path_all_ends(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "t.jsonl")
    out, err = run("find_concept_path", start_concept="hbm_supply", end_concept=None, change="up")
    # hbm_supply → memory_price → semi_earnings
    assert not err
    assert [r["end_concept"] for r in out["results"]] == ["memory_price", "semi_earnings"]
    assert all(r["direction"] == "up" for r in out["results"])


def test_find_concept_path_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "t.jsonl")
    out, err = run("find_concept_path", start_concept="moon", end_concept=None, change="up")
    assert err and "moon" in out


def test_search_event_dates(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "t.jsonl")
    out, err = run("search_event_dates", concept_id="volume_spike", limit=3)
    assert not err
    dates = [e["event_date"] for e in out["events"]]
    assert len(dates) == 3 and dates == sorted(dates, reverse=True)


# --- 도구 정의 ---

def test_tool_schemas_strict_and_match_handlers():
    names = [t["name"] for t in tools.TOOLS]
    assert set(names) == set(tools.HANDLERS) | {"validate_causal_order"}
    for t in tools.TOOLS:
        schema = t["input_schema"]
        assert t["strict"] and schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])



def test_validate_causal_order_pass_and_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "t.jsonl")
    ctx = tools.ToolContext(source_text="한국은행이 기준금리를 3.00%로 동결했다.", ref="macro:bok_2026_10")
    quiz = {"start_concept": "rate_hold", "change": "up", "end_concept": "growth_valuation",
            "answer_order": ["rate_hold", "growth_valuation"], "direction": "down",
            "evidence_quote": "기준금리를 3.00%로 동결했다."}
    content, is_error = tools.run_tool("validate_causal_order", {"quiz": quiz}, ctx)
    assert not is_error and json.loads(content)["passed"] is True

    # 방향을 반대로 쓰면 검증기가 실패 이유를 돌려준다 (도구 실패가 아니라 결과)
    content, is_error = tools.run_tool("validate_causal_order", {"quiz": {**quiz, "direction": "up"}}, ctx)
    out = json.loads(content)
    assert not is_error and out["passed"] is False
    assert any("방향" in e for e in out["errors"])
