"""TradingAgents 시험 실행 (#102). 탭 1 해설 재료 후보: 분석 리포트 + 낙관·비관 토론만 JSON 으로 남긴다.

매매 결론(Buy~Sell, 투자 계획, 트레이더 제안, 리스크 토론, 최종 결정)은 저장하지 않는다.
라이브러리가 스스로 쓰는 전체 상태 로그·메모리 로그(결론 포함)는 임시 폴더에 두고 실행 뒤 지운다.

사용 (tradingagents/.venv 에서):
    python run_report.py --dry-run            # LLM 호출 없이 설정·남은 한도만 확인
    python run_report.py NVDA 2026-11-16      # 1회 실행, 결과 JSON 만 저장
    python run_report.py NVDA 2026-11-16 --save   # + llm_cost_log 에 비용 기록 (월 한도에 반영)
"""
import argparse
import json
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")   # ANTHROPIC_API_KEY, DATABASE_URL, LLM_MONTHLY_LIMIT_USD (값은 출력하지 않는다)

OUT_DIR = HERE / "logs"                       # 루트 .gitignore 의 logs/ 로 커밋되지 않는다
LIB_TMP = OUT_DIR / "_lib_tmp"                # 라이브러리 전용 쓰기 경로 (실행 뒤 삭제)
os.environ.setdefault("TRADINGAGENTS_RESULTS_DIR", str(LIB_TMP / "results"))
os.environ.setdefault("TRADINGAGENTS_CACHE_DIR", str(LIB_TMP / "cache"))
os.environ.setdefault("TRADINGAGENTS_MEMORY_LOG_PATH", str(LIB_TMP / "memory" / "trading_memory.md"))

QUICK = "claude-haiku-4-5"    # 라이브러리 model_catalog 의 anthropic quick 목록에 있음
DEEP = "claude-sonnet-5"      # 라이브러리 model_catalog 의 anthropic deep 목록에 있음
TRANSLATE = QUICK
# 100만 토큰당 USD (Anthropic 공개 단가). 우리 worker 단가표에는 이 두 모델이 없어 여기 둔다.
PRICES = {"claude-haiku-4-5": (1.00, 5.00), "claude-sonnet-5": (2.00, 10.00)}
RUN_BUDGET_USD = 2.00         # 1회 실행 상한 추정치. 남은 월 한도가 이보다 적으면 실행하지 않는다

# 저장하는 것: 분석 리포트 2개 + 낙관·비관 토론. 나머지 state 키는 모두 버린다.
KEEP_REPORTS = ("market_report", "news_report")
KEEP_DEBATE = ("bull_history", "bear_history")
# 라이브러리가 영어로 고정하는 결론 줄 (언어 지시에서 예외). 혹시 섞여 들어와도 지운다.
# "**Rating**:" 와 "**Rating:**" 둘 다 나온다 (#102 실행: bull·bear 끝에 "**Rating:** BUY / ..." 형태)
DECISION_LINE = re.compile(r"^.*(\bRating\b[*\s]*:|FINAL TRANSACTION PROPOSAL).*$", re.M | re.I)
# 사람이 검토할 표현 (지우지 않고 개수만 알린다)
REVIEW_WORDS = re.compile(r"매수|매도|비중\s*확대|비중\s*축소|목표\s*주가|\b(Buy|Sell|Overweight|Underweight)\b")


class UsageByModel:
    """LangChain 콜백. 모델별 입력·출력 토큰과 호출 수를 센다."""

    def __init__(self):
        from langchain_core.callbacks import BaseCallbackHandler

        outer = self

        class Handler(BaseCallbackHandler):
            def on_llm_end(self, response, **kwargs):
                for gens in response.generations:
                    for g in gens:
                        msg = getattr(g, "message", None)
                        usage = getattr(msg, "usage_metadata", None) or {}
                        meta = getattr(msg, "response_metadata", None) or {}
                        outer.add(meta.get("model") or meta.get("model_name") or "unknown",
                                  usage.get("input_tokens", 0), usage.get("output_tokens", 0))

        self.handler = Handler()
        self.lock = threading.Lock()
        self.rows = {}

    def add(self, model, tin, tout):
        with self.lock:
            r = self.rows.setdefault(model, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
            r["calls"] += 1
            r["input_tokens"] += tin
            r["output_tokens"] += tout


def price_of(model):
    for known, p in PRICES.items():
        if model.startswith(known):   # 응답 모델명에 날짜 접미사가 붙을 수 있다
            return known, p
    # 모델명을 못 읽은 호출은 비싼 쪽(deep) 단가로 센다. 실행 뒤에 예외를 내면 결과를 잃는다
    return f"{model}(as {DEEP})", PRICES[DEEP]


def cost_rows(usage):
    out = []
    for model, r in sorted(usage.rows.items()):
        known, (pin, pout) = price_of(model)
        cost = (r["input_tokens"] * pin + r["output_tokens"] * pout) / 1_000_000
        out.append({"model": known, **r, "cost_usd": round(cost, 6)})
    return out


def month_spent(conn):
    return float(conn.execute(
        "SELECT coalesce(sum(cost_usd), 0) FROM llm_cost_log "
        "WHERE called_at >= date_trunc('month', now() AT TIME ZONE 'Asia/Seoul') AT TIME ZONE 'Asia/Seoul'"
    ).fetchone()[0])


def hangul_ratio(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0
    return sum("가" <= c <= "힣" for c in letters) / len(letters)


def to_korean(client, usage, text):
    """한국어 비율이 낮을 때만 번역 (사용자 결정: 토론은 한국어로 저장). 내용은 바꾸지 않고 옮기기만 한다."""
    if not text.strip() or hangul_ratio(text) >= 0.5:
        return text, False
    resp = client.messages.create(
        model=TRANSLATE, max_tokens=8000,
        system="Translate the user's text into natural Korean. Keep numbers, tickers and names as they are. "
               "Do not add, remove or summarize anything. Output only the translation.",
        messages=[{"role": "user", "content": text}],
    )
    usage.add(resp.model, resp.usage.input_tokens, resp.usage.output_tokens)
    return "".join(b.text for b in resp.content if b.type == "text"), True


def clean(text):
    return DECISION_LINE.sub("", text or "").strip()


def build_config():
    from tradingagents.default_config import DEFAULT_CONFIG

    cfg = DEFAULT_CONFIG.copy()
    cfg.update({
        "llm_provider": "anthropic",
        "deep_think_llm": DEEP,
        "quick_think_llm": QUICK,
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,   # 리스크 토론은 저장하지 않지만 그래프에서 끌 수 없어 최소로
        "output_language": "Korean",
    })
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker", nargs="?", default="NVDA")
    ap.add_argument("date", nargs="?", default="2026-11-16")
    ap.add_argument("--dry-run", action="store_true", help="LLM 을 부르지 않고 설정과 남은 한도만 출력")
    ap.add_argument("--save", action="store_true", help="비용을 llm_cost_log 에 기록")
    args = ap.parse_args()

    import psycopg
    import tradingagents
    from tradingagents.llm_clients.model_catalog import get_known_models

    known = get_known_models()["anthropic"]
    for m in (QUICK, DEEP):
        if m not in known:
            sys.exit(f"라이브러리 모델 목록에 없는 모델: {m} (목록: {known})")

    limit = float(os.environ.get("LLM_MONTHLY_LIMIT_USD", "10"))
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        spent = month_spent(conn)
    print(f"tradingagents {tradingagents.__version__} | quick={QUICK} deep={DEEP} | analysts=market,news")
    print(f"이번 달 사용 ${spent:.4f} / 한도 ${limit:.2f} | 1회 상한 추정 ${RUN_BUDGET_USD:.2f}")
    if spent + RUN_BUDGET_USD > limit:
        sys.exit("남은 월 한도가 1회 상한 추정보다 적어 실행하지 않습니다.")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY 가 루트 .env 에 없습니다.")
    if args.dry_run:
        print("dry-run: 여기서 멈춤")
        return

    from anthropic import Anthropic
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    usage = UsageByModel()
    started = time.monotonic()
    try:
        ta = TradingAgentsGraph(selected_analysts=("market", "news"), config=build_config(),
                                callbacks=[usage.handler])
        final_state, _rating = ta.propagate(args.ticker, args.date)   # _rating(매매 결론)은 쓰지 않는다
        graph_sec = time.monotonic() - started
        print("final_state.keys():", sorted(final_state.keys()))
        print("investment_debate_state.keys():", sorted(final_state["investment_debate_state"].keys()))

        client = Anthropic()
        translated = []
        reports = {}
        for k in KEEP_REPORTS:
            reports[k], t = to_korean(client, usage, clean(final_state.get(k)))
            if t:
                translated.append(k)
        debate = {}
        for k in KEEP_DEBATE:
            debate[k], t = to_korean(client, usage, clean(final_state["investment_debate_state"].get(k)))
            if t:
                translated.append(k)
    finally:
        shutil.rmtree(LIB_TMP, ignore_errors=True)   # 결론이 든 라이브러리 로그 삭제

    total_sec = time.monotonic() - started
    costs = cost_rows(usage)
    total_cost = round(sum(r["cost_usd"] for r in costs), 6)
    texts = {**reports, **debate}
    out = {
        "ticker": args.ticker,
        "analysis_date": args.date,
        "source": f"TradingAgents {tradingagents.__version__}",
        "reports": reports,
        "debate": {"bull": debate["bull_history"], "bear": debate["bear_history"]},
        "meta": {
            "models": {"quick": QUICK, "deep": DEEP},
            "analysts": ["market", "news"],
            "max_debate_rounds": 1,
            "output_language": "Korean",
            "translated_fields": translated,
            "hangul_ratio": {k: round(hangul_ratio(v), 2) for k, v in texts.items()},
            "review_word_hits": {k: len(REVIEW_WORDS.findall(v)) for k, v in texts.items()},
            "graph_seconds": round(graph_sec, 1),
            "total_seconds": round(total_sec, 1),
            "usage": costs,
            "cost_usd": total_cost,
        },
    }
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{args.ticker}_{args.date}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장: {path}")
    print(json.dumps(out["meta"], ensure_ascii=False, indent=2))

    if args.save:
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            for r in costs:
                conn.execute(
                    "INSERT INTO llm_cost_log (module, model, input_tokens, output_tokens, cost_usd, note) "
                    "VALUES ('tradingagents', %s, %s, %s, %s, %s)",
                    (r["model"], r["input_tokens"], r["output_tokens"], r["cost_usd"],
                     f"#102 시험 {args.ticker} {args.date} calls={r['calls']}"),
                )
        print("llm_cost_log 기록 완료")


if __name__ == "__main__":
    main()
