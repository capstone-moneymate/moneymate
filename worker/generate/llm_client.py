"""Claude 공통 호출 모듈. classify·compose·reasons 등은 Claude를 이 모듈로만 부른다.

사용 예:
    from generate.llm_client import create, text_of
    resp = create("classify", model=HAIKU, max_tokens=256, messages=[...])
    print(text_of(resp))

하는 일
1. 호출 전: 이번 달(KST) 누적 비용이 LLM_MONTHLY_LIMIT_USD 이상이면 BudgetExceeded 로 막는다.
   호출 1번이 한도를 조금 넘길 수는 있다 (응답을 받아야 비용을 알 수 있어서).
2. 호출: anthropic SDK messages.create 를 그대로 부른다. 429·5xx·연결 오류는 SDK가 2회 재시도하고,
   그래도 실패하면 예외를 그대로 올린다 (재생성 여부는 부른 쪽이 정한다).
3. 호출 후: resp.usage 로 비용을 계산해 llm_cost_log 에 1줄 남긴다.
   DB에 못 쓰면 레포 루트 logs/llm_cost_log.jsonl 에 대신 남긴다 (check_claude_call.py 와 같은 방식).
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
import psycopg

import config
from db import get_conn

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "logs" / "llm_cost_log.jsonl"
KST = timezone(timedelta(hours=9))  # 한국은 서머타임이 없어 고정 +9 로 충분하다

HAIKU = "claude-haiku-5-5"  # 분류·매칭
SONNET = "claude-sonnet-5-5"  # 출제·채점

# USD per 1M tokens (2026-10 기준). long: 입력이 100K 토큰을 넘을 때 단가
PRICES = {
    HAIKU: {"input": 0.10, "output": 0.50, "long": {"input": 0.50, "output": 2.50}},
    SONNET: {"input": 2.00, "output": 10.00},
}
LONG_CONTEXT_TOKENS = 100_000
# 프롬프트 캐시 단가 = 입력 단가 × 배수 (쓰기 5분 캐시 1.25배, 읽기 0.1배)
CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = 0.1


class BudgetExceeded(RuntimeError):
    """이번 달 누적 비용이 월 한도에 닿아 호출을 막았다."""


def cost_usd(model: str, usage) -> float:
    """resp.usage 로 비용(USD)을 계산한다. 캐시 쓰기·읽기 토큰도 포함한다."""
    if model not in PRICES:
        raise ValueError(f"단가가 없는 모델입니다: {model} (llm_client.PRICES 에 추가)")
    plain = usage.input_tokens or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", None) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", None) or 0
    price = PRICES[model]
    if plain + cache_write + cache_read > LONG_CONTEXT_TOKENS and "long" in price:
        price = price["long"]
    input_cost = price["input"] * (
        plain + cache_write * CACHE_WRITE_MULT + cache_read * CACHE_READ_MULT
    )
    # 생각(thinking) 토큰도 output_tokens 에 포함되어 과금된다
    return (input_cost + usage.output_tokens * price["output"]) / 1_000_000


def month_start(now: datetime | None = None) -> datetime:
    """KST 기준 이번 달 1일 0시."""
    now = (now or datetime.now(timezone.utc)).astimezone(KST)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def month_spent(now: datetime | None = None) -> float:
    """이번 달(KST) 누적 비용. DB에 못 읽으면 jsonl 로그로 계산한다."""
    start = month_start(now)
    try:
        with get_conn() as conn:
            total = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_cost_log WHERE called_at >= %s",
                (start,),
            ).fetchone()[0]
        return float(total)
    except psycopg.Error:
        return _jsonl_spent(start)


def _jsonl_spent(start: datetime) -> float:
    if not LOG_PATH.exists():
        return 0.0
    total = 0.0
    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if datetime.fromisoformat(row["called_at"]) >= start:
                total += row["cost_usd"]
    return total


def check_budget() -> float:
    """월 한도를 넘었으면 BudgetExceeded. 넘지 않았으면 이번 달 누적 비용을 돌려준다."""
    spent = month_spent()
    if spent >= config.LLM_MONTHLY_LIMIT_USD:
        raise BudgetExceeded(
            f"이번 달 LLM 비용 ${spent:.4f} 가 월 한도 ${config.LLM_MONTHLY_LIMIT_USD} 에 닿았습니다."
        )
    return spent


def record(row: dict) -> str:
    """llm_cost_log 에 1줄 남긴다. 기록한 곳('db' 또는 'jsonl')을 돌려준다."""
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO llm_cost_log
                    (called_at, module, model, input_tokens, output_tokens, cost_usd, card_id, note)
                VALUES (%(called_at)s, %(module)s, %(model)s, %(input_tokens)s,
                        %(output_tokens)s, %(cost_usd)s, %(card_id)s, %(note)s)
                """,
                row,
            )
        return "db"
    except psycopg.Error as e:
        print(f"llm_cost_log DB 기록 실패 ({e.__class__.__name__}), jsonl 에 남깁니다.", file=sys.stderr)
        LOG_PATH.parent.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({**row, "called_at": row["called_at"].isoformat()}, ensure_ascii=False) + "\n")
        return "jsonl"


_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # .env 의 ANTHROPIC_API_KEY (config import 때 환경변수로 올라감)
    return _client


def create(module: str, *, card_id: int | None = None, note: str | None = None, **params):
    """한도 확인 → messages.create → 비용 기록. params 는 messages.create 인자 그대로.

    module: llm_cost_log.module 값 (classify / compose / reasons / judge ...)
    card_id: 카드가 이미 있으면 넣는다 (문제 1개당 비용 집계용). 없으면 None.
    """
    check_budget()
    resp = get_client().messages.create(**params)

    usage = resp.usage
    cache_note = ""
    if usage.cache_creation_input_tokens or usage.cache_read_input_tokens:
        cache_note = f" cache_write={usage.cache_creation_input_tokens or 0} cache_read={usage.cache_read_input_tokens or 0}"
    record(
        {
            "called_at": datetime.now(timezone.utc),
            "module": module,
            "model": resp.model,
            # 캐시 토큰까지 합친 전체 입력 토큰 (나눈 값은 note 에)
            "input_tokens": (usage.input_tokens or 0)
            + (usage.cache_creation_input_tokens or 0)
            + (usage.cache_read_input_tokens or 0),
            "output_tokens": usage.output_tokens,
            "cost_usd": round(cost_usd(params["model"], usage), 6),
            "card_id": card_id,
            "note": " ".join(
                s for s in (f"request_id={resp._request_id}{cache_note}", f"stop={resp.stop_reason}", note) if s
            ),
        }
    )
    return resp


def text_of(resp) -> str:
    """응답의 text 블록만 이어 붙인다 (thinking·tool_use 블록은 뺀다)."""
    return "".join(block.text for block in resp.content if block.type == "text")
