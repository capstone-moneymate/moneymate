"""Claude를 1회 호출하고 비용을 llm_cost_log에 남긴다 (1주차 확인용).

실행: cd worker && python scripts/check_claude_call.py
필요: pip install anthropic, .env 의 ANTHROPIC_API_KEY (Anthropic Console에서 월 사용 한도를 먼저 설정)
      DB에 쓰려면 docker compose up -d 로 PostgreSQL을 띄워 둔다.

resp.usage의 토큰 수로 비용을 계산해 llm_cost_log에 INSERT한다.
DB에 못 쓰면(안 띄움 등) 레포 루트 logs/llm_cost_log.jsonl 에 대신 남긴다.
3주차 generate/llm_client.py 가 이 계산·기록 부분을 이어받는다.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

import anthropic  # noqa: E402
import psycopg  # noqa: E402

import config  # noqa: E402,F401  레포 루트 .env 를 읽어 ANTHROPIC_API_KEY 를 환경변수로 올린다
from db import get_conn  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MODEL = "claude-haiku-5-5"  # 분류·매칭용 모델. 출제는 claude-sonnet-5-5
# USD per 1M tokens (2026-10 기준, 입력 100K 토큰 이하 구간)
PRICES = {
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00},
}
MODULE = "week1_check"
PROMPT = "기준금리 동결이 은행주에 주는 영향을 초보 투자자에게 한 문장으로 설명해줘."


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICES[model]
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000


def save_to_db(row: dict) -> bool:
    """llm_cost_log 에 INSERT. DB에 못 쓰면 False."""
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO llm_cost_log (called_at, module, model, input_tokens, output_tokens, cost_usd, note)
                VALUES (%(called_at)s, %(module)s, %(model)s, %(input_tokens)s,
                        %(output_tokens)s, %(cost_usd)s, %(note)s)
                """,
                row,
            )
        return True
    except psycopg.Error as e:
        print(f"DB 기록 실패 ({e.__class__.__name__}): {e}", file=sys.stderr)
        return False


def main() -> int:
    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": PROMPT}],
        )
    except anthropic.AuthenticationError:
        print("API 키가 없거나 틀렸습니다. 레포 루트 .env 의 ANTHROPIC_API_KEY 를 확인하세요.", file=sys.stderr)
        return 1
    except anthropic.RateLimitError as e:
        print(f"한도 초과(429): {e}", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as e:
        print(f"API 오류 {e.status_code}: {e}", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError as e:
        print(f"연결 실패: {e}", file=sys.stderr)
        return 1

    if resp.stop_reason == "refusal":
        print(f"응답 거절: {resp.stop_details}", file=sys.stderr)
    text = "".join(block.text for block in resp.content if block.type == "text")

    usage = resp.usage
    row = {
        "called_at": datetime.now(timezone.utc),
        "module": MODULE,
        "model": MODEL,
        "input_tokens": usage.input_tokens,
        # 생각(thinking) 토큰도 output_tokens 에 포함되어 과금된다
        "output_tokens": usage.output_tokens,
        "cost_usd": round(cost_usd(MODEL, usage.input_tokens, usage.output_tokens), 6),
        "note": f"request_id={resp._request_id}",
    }

    print(f"응답: {text}")
    print(f"토큰: 입력 {row['input_tokens']}, 출력 {row['output_tokens']} → ${row['cost_usd']:.6f}")

    if save_to_db(row):
        print("llm_cost_log(DB)에 기록했습니다.")
    else:
        out = ROOT / "logs" / "llm_cost_log.jsonl"
        out.parent.mkdir(exist_ok=True)
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps({**row, "called_at": row["called_at"].isoformat()}, ensure_ascii=False) + "\n")
        print(f"대신 {out.relative_to(ROOT)} 에 기록했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
