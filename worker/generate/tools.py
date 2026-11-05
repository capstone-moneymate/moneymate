"""출제 에이전트(compose)가 쓰는 도구. 숫자·경로·검증은 전부 여기 코드가 계산하고, Claude는 결과를 받아 문장만 쓴다.

사용 예 (compose 의 tool use 루프 안):
    from generate.tools import TOOLS, ToolContext, run_tool
    ctx = ToolContext(source_text="...", ref="dart:20261008000123")
    content, is_error = run_tool(block.name, block.input, ctx)   # tool_result 로 돌려준다

도구 (기술확정안 "문제 생성·검증" 5·6·7단계)
- calc_rsi: 그날 RSI (Wilder, 기본 14일)
- calc_return: 두 날짜 사이 종가 수익률(%)
- volume_stats: 그날 거래량 ÷ 직전 252거래일 평균, 그날까지 최근 N거래일 거래량 상위일
- find_concept_path: 시작 개념 → 결과 개념 경로와 방향 (B의 concepts/graph.py)
- search_event_dates: 비슷했던 과거의 날 (db/seeds/event_dates.csv)
- validate_causal_order: 인과 순서 문제 검증 (B의 validate/validators.py)
- validate_chart_answer: 차트 문제에 쓴 숫자·날짜를 코드가 다시 계산해 비교

원시 종가·거래량을 돌려주는 도구는 두지 않는다. 에이전트가 숫자를 직접 계산할 여지를 없애기 위해서다.

규칙
- 도구가 실패해도 예외를 올리지 않고 (오류 문장, is_error=True)를 돌려준다. 에이전트가 이유를 보고 고친다.
- 도구 호출은 레포 루트 logs/tool_calls.jsonl 에 1줄씩 남긴다 (도구·입력·성공 여부·걸린 시간).
"""
import csv
import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from concepts.graph import effect, load_graph
from db import get_conn
from validate.validators import verify

ROOT = Path(__file__).resolve().parents[2]
SEEDS = ROOT / "db" / "seeds"
LOG_PATH = ROOT / "logs" / "tool_calls.jsonl"
AVG_DAYS = 252  # 비정상 거래량 기준 (source_select 와 같음)
MAX_WINDOW = 20  # volume_stats 가 상위일을 찾는 최근 거래일 수 상한
TOLERANCE = 0.01  # 숫자 정답 비교 허용 오차 (소수 둘째 자리 반올림 차이)


class ToolError(Exception):
    """에이전트에게 그대로 보여줄 오류 (입력이 틀렸거나 데이터가 없음)."""


@dataclass
class ToolContext:
    source_text: str = ""  # 카드의 1차 자료 원문(제목·숫자). 검증기가 근거 인용을 대조한다. 에이전트가 바꿀 수 없다
    ref: str | None = None  # 로그에 남길 자료 키 (source_type:source_key)


# --- 데이터 읽기 ---

def load_prices(ticker: str, end: date, n: int) -> pd.DataFrame:
    """end 이하 마지막 n 거래일. 컬럼 market_date, close, volume (날짜 오름차순)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT market_date, close, volume FROM prices
               WHERE ticker = %s AND market_date <= %s ORDER BY market_date DESC LIMIT %s""",
            (ticker, end, n),
        ).fetchall()
    df = pd.DataFrame(rows, columns=["market_date", "close", "volume"])
    if df.empty:
        raise ToolError(f"{ticker} 의 {end} 이전 가격이 없어요. 티커 형식(국내 6자리, 미국 대문자, 지수 KS11 등)을 확인하세요")
    df["close"] = df["close"].astype(float)
    return df.iloc[::-1].reset_index(drop=True)


def load_range(ticker: str, start: date, end: date) -> pd.DataFrame:
    df = load_prices(ticker, end, AVG_DAYS * 2)
    df = df[df["market_date"] >= start].reset_index(drop=True)
    if df.empty:
        raise ToolError(f"{ticker} 의 {start}~{end} 거래일이 없어요")
    return df


# --- 계산 (DB 없이 테스트하는 순수 함수) ---

def wilder_rsi(closes: list[float], period: int = 14) -> float:
    """마지막 날 RSI. 첫 평균은 처음 period 개 변화의 단순 평균, 그다음은 Wilder 평활
    (평균 = (이전 평균 × (period-1) + 오늘 값) ÷ period). 손실이 0이면 100."""
    if len(closes) < period + 1:
        raise ToolError(f"RSI {period}일을 계산하려면 종가가 {period + 1}개 이상 필요해요 (지금 {len(closes)}개)")
    diffs = [b - a for a, b in zip(closes, closes[1:])]
    gain = sum(max(d, 0) for d in diffs[:period]) / period
    loss = sum(max(-d, 0) for d in diffs[:period]) / period
    for d in diffs[period:]:
        gain = (gain * (period - 1) + max(d, 0)) / period
        loss = (loss * (period - 1) + max(-d, 0)) / period
    if loss == 0:
        return 100.0
    return round(100 - 100 / (1 + gain / loss), 2)


def pct_return(start_close: float, end_close: float) -> float:
    return round((end_close / start_close - 1) * 100, 2)


def volume_ratio(volumes: list[float]) -> float:
    """마지막 날 거래량 ÷ 그 앞 날들 평균."""
    *before, today = volumes
    if not before:
        raise ToolError("평균을 낼 이전 거래일이 없어요")
    avg = sum(before) / len(before)
    return round(today / avg, 2) if avg else 0.0


def top_volume_days(df: pd.DataFrame, n: int) -> list[dict]:
    """거래량 큰 순 n 일. 같으면 이른 날 먼저."""
    top = df.sort_values(["volume", "market_date"], ascending=[False, True]).head(n)
    return [{"date": str(r.market_date), "volume": int(r.volume)} for r in top.itertuples()]


# --- 도구 본체 ---

def _date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        raise ToolError(f"날짜는 YYYY-MM-DD 형식이어야 해요: {s}") from None


def calc_rsi(ticker: str, date: str, period: int) -> dict:
    df = load_prices(ticker, _date(date), AVG_DAYS)
    return {"ticker": ticker, "date": str(df["market_date"].iloc[-1]), "period": period,
            "rsi": wilder_rsi(df["close"].tolist(), period)}


def calc_return(ticker: str, start_date: str, end_date: str) -> dict:
    df = load_range(ticker, _date(start_date), _date(end_date))
    first, last = df.iloc[0], df.iloc[-1]
    return {"ticker": ticker, "start": str(first.market_date), "end": str(last.market_date),
            "return_pct": pct_return(first.close, last.close)}


def volume_stats(ticker: str, date: str, days: int) -> dict:
    if not 1 <= days <= MAX_WINDOW:
        raise ToolError(f"days 는 1~{MAX_WINDOW} 사이여야 해요: {days}")
    d = _date(date)
    hist = load_prices(ticker, d, AVG_DAYS + 1)
    if str(hist["market_date"].iloc[-1]) != str(d):
        raise ToolError(f"{d} 은 {ticker} 의 거래일이 아니에요")
    window = hist.tail(days)
    return {"ticker": ticker, "date": str(d), "avg_days": len(hist) - 1,
            "ratio_to_avg": volume_ratio(hist["volume"].astype(float).tolist()),
            "window": [str(x) for x in window["market_date"]],
            "window_top": top_volume_days(window, 3)}


METRICS = ("return_pct", "volume_ratio", "top_volume_date", "rsi")


def validate_chart_answer(metric: str, ticker: str, start_date: str | None, end_date: str, value: str) -> dict:
    """에이전트가 문제·해설에 쓴 값(value)을 코드가 다시 계산한 값과 비교한다.
    return_pct: start~end 수익률(%) / volume_ratio: end 거래량 ÷ 직전 252일 평균 /
    top_volume_date: start~end 중 거래량이 가장 큰 날 / rsi: end 의 RSI(14)."""
    if metric not in METRICS:
        raise ToolError(f"metric 은 {', '.join(METRICS)} 중 하나여야 해요: {metric}")
    if metric in ("return_pct", "top_volume_date") and not start_date:
        raise ToolError(f"{metric} 는 start_date 가 필요해요")
    if metric == "return_pct":
        expected = calc_return(ticker, start_date, end_date)["return_pct"]
    elif metric == "volume_ratio":
        expected = volume_stats(ticker, end_date, 1)["ratio_to_avg"]
    elif metric == "rsi":
        expected = calc_rsi(ticker, end_date, 14)["rsi"]
    else:
        expected = top_volume_days(load_range(ticker, _date(start_date), _date(end_date)), 1)[0]["date"]

    if metric == "top_volume_date":
        passed = value.strip() == expected
    else:
        try:
            passed = bool(abs(float(value.replace("%", "").replace("배", "").strip()) - expected) <= TOLERANCE)
        except ValueError:
            raise ToolError(f"value 는 숫자여야 해요: {value}") from None
    out = {"passed": passed, "metric": metric, "expected": expected, "given": value}
    if not passed:
        out["error"] = f"코드가 계산한 값은 {expected} 이에요. 문제·보기·해설의 숫자를 이 값으로 고치세요"
    return out


def find_concept_path(start_concept: str, end_concept: str | None, change: str) -> dict:
    g = load_graph()
    if start_concept not in g.out:
        raise ToolError(f"개념 사전에 없는 개념: {start_concept}")
    ends = [end_concept] if end_concept else _reachable(g, start_concept)
    results = []
    for end in ends:
        if end not in g.out:
            raise ToolError(f"개념 사전에 없는 개념: {end}")
        e = effect(g, start_concept, end, change)
        results.append({
            "end_concept": end,
            "direction": e.direction,  # up / down / ambiguous / None(경로 없음)
            "paths": [{"concept_ids": p, "names": [g.names[c] for c in p]} for p, _ in e.paths],
        })
    return {"start_concept": start_concept, "change": change, "results": results}


def _reachable(g, start: str) -> list[str]:
    seen, stack = [], [start]
    while stack:
        for nxt, _ in g.out[stack.pop()]:
            if nxt not in seen and nxt != start:
                seen.append(nxt)
                stack.append(nxt)
    return sorted(seen)


def search_event_dates(concept_id: str, limit: int) -> dict:
    with open(SEEDS / "event_dates.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["concept_id"] == concept_id]
    rows.sort(key=lambda r: r["event_date"], reverse=True)
    keep = ("event_date", "market", "ticker", "event_type", "value", "note")
    return {"concept_id": concept_id, "events": [{k: r[k] for k in keep} for r in rows[: max(1, min(limit, 10))]]}


def validate_causal_order(quiz: dict, ctx: ToolContext) -> dict:
    report = verify(quiz, ctx.source_text)
    return {"passed": report.passed, "errors": report.errors, "warnings": report.warnings}


# --- Claude 에게 넘길 도구 정의 (strict: 스키마에 맞는 입력만 온다) ---

def _tool(name: str, description: str, props: dict) -> dict:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {"type": "object", "properties": props, "required": list(props), "additionalProperties": False},
    }


TICKER = {"type": "string", "description": "국내 6자리 문자열('005930'), 미국 대문자('NVDA'), 지수 키('KS11')"}
DATE = {"type": "string", "description": "YYYY-MM-DD"}
CHANGE = {"type": "string", "enum": ["up", "down"], "description": "시작 개념이 커지거나 일어났으면 up, 줄었으면 down"}

TOOLS = [
    _tool("calc_rsi", "그날(거래일이 아니면 직전 거래일) RSI. Wilder 방식.",
          {"ticker": TICKER, "date": DATE, "period": {"type": "integer", "description": "보통 14"}}),
    _tool("calc_return", "두 날짜 사이 종가 수익률(%). 시작일·종료일이 거래일이 아니면 그 안쪽 첫·마지막 거래일.",
          {"ticker": TICKER, "start_date": DATE, "end_date": DATE}),
    _tool("volume_stats", "그날 거래량이 직전 252거래일 평균의 몇 배인지, 그날까지 최근 days 거래일 중 거래량 상위 3일.",
          {"ticker": TICKER, "date": DATE, "days": {"type": "integer", "description": "1~20. 예: 3일 연속 상승이면 3"}}),
    _tool("find_concept_path",
          "개념 사전에서 시작 개념 → 결과 개념 경로와 결과 방향(up/down/ambiguous). end_concept 가 null 이면 닿는 모든 결과.",
          {"start_concept": {"type": "string"}, "end_concept": {"type": ["string", "null"]}, "change": CHANGE}),
    _tool("search_event_dates", "그 개념이 나타났던 과거의 날 (최신순, 최대 10개).",
          {"concept_id": {"type": "string"}, "limit": {"type": "integer"}}),
    _tool("validate_causal_order",
          "인과 순서 문제를 개념 사전·원문과 대조. passed 가 false 면 errors 를 보고 고치세요.",
          {"quiz": {
              "type": "object",
              "properties": {
                  "start_concept": {"type": "string"}, "change": CHANGE, "end_concept": {"type": "string"},
                  "answer_order": {"type": "array", "items": {"type": "string"}},
                  "direction": {"type": "string", "enum": ["up", "down"]},
                  "evidence_quote": {"type": "string", "description": "원문 문장 그대로"},
              },
              "required": ["start_concept", "change", "end_concept", "answer_order", "direction", "evidence_quote"],
              "additionalProperties": False,
          }}),
    _tool("validate_chart_answer",
          "차트 문제의 정답·해설에 쓴 숫자나 날짜를 코드가 다시 계산해 비교. 문제를 내기 전에 정답마다 한 번씩 부르세요. "
          "return_pct: start~end 수익률(%), volume_ratio: end 거래량 ÷ 252일 평균, "
          "top_volume_date: start~end 거래량 최대일(YYYY-MM-DD), rsi: end 의 RSI(14).",
          {"metric": {"type": "string", "enum": list(METRICS)}, "ticker": TICKER,
           "start_date": {"type": ["string", "null"], "description": "return_pct·top_volume_date 만. 나머지는 null"},
           "end_date": DATE, "value": {"type": "string", "description": "문제에 쓴 값 (예: '2.4', '2026-10-08')"}}),
]

HANDLERS = {
    "calc_rsi": calc_rsi,
    "calc_return": calc_return,
    "volume_stats": volume_stats,
    "find_concept_path": find_concept_path,
    "search_event_dates": search_event_dates,
    "validate_chart_answer": validate_chart_answer,
}


def run_tool(name: str, args: dict, ctx: ToolContext | None = None) -> tuple[str, bool]:
    """도구 1회 실행 → (tool_result 에 넣을 JSON 문자열, is_error). 로그 1줄."""
    ctx = ctx or ToolContext()
    t0 = time.perf_counter()
    try:
        if name == "validate_causal_order":
            out = validate_causal_order(args["quiz"], ctx)
        elif name in HANDLERS:
            out = HANDLERS[name](**args)
        else:
            raise ToolError(f"없는 도구: {name}")
        content, is_error = json.dumps(out, ensure_ascii=False, default=str), False
    except ToolError as e:
        content, is_error = str(e), True
    except Exception as e:  # DB 연결 실패 등. 에이전트에게는 짧게, 로그에는 종류를 남긴다
        content, is_error = f"도구 실행 실패 ({type(e).__name__}). 다른 방법으로 진행하세요", True
    _log(name, args, ctx, is_error, content if is_error else None, time.perf_counter() - t0)
    return content, is_error


def _log(name, args, ctx, is_error, error, seconds) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {"called_at": datetime.now(timezone.utc).isoformat(), "tool": name, "ref": ctx.ref,
           "input": args, "ok": not is_error, "error": error, "ms": round(seconds * 1000)}
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
