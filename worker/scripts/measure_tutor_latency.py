"""튜터 에이전트(1-3) 모델 고르기용 응답 시간 측정 (사람1, 시험용). 실제 튜터 코드가 아니다.
튜터 한 단계와 같은 크기의 요청(도구 4개 + 지식 상태 + "다음에 무엇을 할지")을 모델·effort 조건마다 여러 번 보내
걸린 시간, 고른 도구, 비용을 잰다.

실행 (worker/ 에서): python -m scripts.measure_tutor_latency [반복 수, 기본 5]
결과: 화면 + logs/tutor_latency.json. 비용은 llm_cost_log 에도 남는다 (월 한도 계산에 들어감).

주의: llm_client.PRICES 에 Opus 가 없어 create() 대신 get_client() 로 부르고 비용은 여기서 계산한다.
"""
import json
import statistics
import sys
import time
from datetime import datetime, timezone

from generate.llm_client import ROOT, check_budget, get_client, record

PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00)}  # USD / 1M 토큰 (입력, 출력)
CONDITIONS = [
    ("claude-opus-5-5", "low"),
    ("claude-sonnet-5-5", "low"),
]
KINDS = ["용어 뜻", "헷갈리는 쌍", "틀린 설명", "O/X", "칩 빈칸", "짝 맞추기", "사례 분류"]


def _tool(name: str, desc: str, props: dict) -> dict:
    return {"name": name, "description": desc, "strict": True,
            "input_schema": {"type": "object", "properties": props, "required": list(props),
                             "additionalProperties": False}}


TOOLS = [
    _tool("ready_concepts", "배울 준비가 된 개념과 알 확률을 다시 본다.", {}),
    _tool("ask_quiz", "개념 하나를 퀴즈로 확인한다. 종류마다 확인하는 것과 찍어서 맞힐 확률이 다르다.",
          {"concept": {"type": "string"}, "kind": {"type": "string", "enum": KINDS}}),
    _tool("explain", "개념을 짧게 설명한다.",
          {"concept": {"type": "string"}, "style": {"type": "string", "enum": ["예시 위주", "정의 위주"]}}),
    _tool("go_main", "개념 단계를 끝내고 뉴스 본 문제로 넘어간다.", {}),
]

SYSTEM = "\n".join([
    "너는 경제 초보자 학습 서비스의 튜터다. 뉴스 본 문제 전에, 그 뉴스를 이해하는 데 필요한 개념을 짧게 확인하고 가르친다.",
    "도구 결과를 보고 다음에 할 일을 스스로 하나 고른다. 고정된 순서는 없다.",
    "퀴즈 종류 고르는 근거: 처음 보는 개념 → 용어 뜻, 헷갈리는 이웃이 있음 → 헷갈리는 쌍, 긴가민가 → 칩 빈칸·사례 분류,",
    "확신했는데 틀렸던 개념 → 틀린 설명, 거의 앎 → O/X. 목표 개념을 다 알면 go_main.",
    "한 번에 도구 하나만 부른다.",
])

CARD = "삼성전자 자사주 소각 발표"
TARGETS = ["주당순이익", "자사주 소각"]

# (이름, 상태, 맞다고 보는 선택). 선택은 "도구" 또는 "ask_quiz:종류". 기준은 SYSTEM 의 규칙이다
# (모델이 규칙을 얼마나 일관되게 따르는지 보는 것이지, 교육적으로 정답이라는 뜻은 아니다)
SCENARIOS = [
    ("확신했는데 틀림", {
        "ready_concepts": [{"concept": "유통 주식 수", "p_know": 0.42, "neighbors": ["발행주식 총수"]},
                           {"concept": "순이익", "p_know": 0.71, "neighbors": []}],
        "history": [{"concept": "유통 주식 수", "kind": "용어 뜻", "correct": False, "confidence": "확신해요"}],
        "steps_used": 1}, {"ask_quiz:틀린 설명"}),
    ("처음 보는 개념", {
        "ready_concepts": [{"concept": "순이익", "p_know": 0.20, "neighbors": []}],
        "history": [], "steps_used": 0}, {"ask_quiz:용어 뜻"}),
    ("헷갈리는 이웃", {
        "ready_concepts": [{"concept": "주당순이익", "p_know": 0.50, "neighbors": ["주당순자산"]}],
        "history": [{"concept": "순이익", "kind": "용어 뜻", "correct": True, "confidence": "확신해요"}],
        "steps_used": 1}, {"ask_quiz:헷갈리는 쌍"}),
    ("거의 앎", {
        "ready_concepts": [{"concept": "자사주 소각", "p_know": 0.90, "neighbors": []}],
        "history": [{"concept": "자사주 소각", "kind": "칩 빈칸", "correct": True, "confidence": "확신해요"}],
        "steps_used": 2}, {"ask_quiz:O/X"}),
    ("긴가민가", {
        "ready_concepts": [{"concept": "자사주 소각", "p_know": 0.60, "neighbors": []}],
        "history": [{"concept": "자사주 소각", "kind": "용어 뜻", "correct": True, "confidence": "애매해요"}],
        "steps_used": 1}, {"ask_quiz:칩 빈칸", "ask_quiz:사례 분류"}),
    ("목표 다 앎", {
        "ready_concepts": [],
        "known": [{"concept": "주당순이익", "p_know": 0.97}, {"concept": "자사주 소각", "p_know": 0.96}],
        "history": [{"concept": "주당순이익", "kind": "O/X", "correct": True, "confidence": "확신해요"}],
        "steps_used": 4}, {"go_main"}),
]


def state(s: dict) -> dict:
    return {"card": CARD, "target_concepts": TARGETS, **s, "max_steps": 6}


def choice_key(uses) -> str:
    """고른 행동. 도구를 하나만 불러야 맞을 수 있다 (SYSTEM 이 한 번에 하나만 부르라고 한다).
    여러 개를 부르면 "(도구 N개)"로 남겨 틀린 것으로 센다 (#204 리뷰: 전에는 첫 번째만 봤다)."""
    if not uses:
        return "(도구 없음)"
    if len(uses) > 1:
        return f"(도구 {len(uses)}개)"
    u = uses[0]
    return f"ask_quiz:{u.input.get('kind')}" if u.name == "ask_quiz" else u.name


def call_once(model: str, effort: str, st: dict) -> dict:
    check_budget()
    start = time.perf_counter()
    resp = get_client().messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM,
        tools=TOOLS,
        tool_choice={"type": "auto"},
        output_config={"effort": effort},
        messages=[{"role": "user", "content": "<state>\n" + json.dumps(st, ensure_ascii=False) + "\n</state>\n다음에 할 일을 골라."}],
    )
    sec = time.perf_counter() - start
    inp, out = PRICES[model]
    u = resp.usage
    cost = ((u.input_tokens or 0) * inp + u.output_tokens * out) / 1_000_000
    record({"called_at": datetime.now(timezone.utc), "module": "tutor_latency", "model": resp.model,
            "input_tokens": u.input_tokens or 0, "output_tokens": u.output_tokens, "cost_usd": round(cost, 6),
            "card_id": None, "note": f"request_id={resp._request_id} stop={resp.stop_reason} effort={effort}"})
    uses = [b for b in resp.content if b.type == "tool_use"]
    return {"sec": round(sec, 2), "pick": choice_key(uses), "out_tokens": u.output_tokens, "cost": cost}


def p90(xs: list[float]) -> float:
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(0.9 * (len(s) - 1))))]


def main(argv: list[str]) -> None:
    n = int(argv[0]) if argv else 4
    (ROOT / "logs").mkdir(exist_ok=True)  # 돈 드는 호출 전에. 새로 받은 저장소에는 logs/ 가 없다 (#204 리뷰)
    call_once(*CONDITIONS[-1], state(SCENARIOS[0][1]))  # 첫 연결 시간이 한 조건에만 섞이지 않게 버리는 호출
    runs = []  # (조건, 상황 이름, 결과, 맞음)
    raw = []   # 부른 순서 그대로 (순번, 반복, 상황, 모델, 시간, 고른 것). 순서 효과를 나중에 확인할 수 있게
    k = 0
    for rep in range(n):  # 상황·조건을 번갈아 불러 시간대에 따른 서버 상황 차이를 고르게 나눈다
        for si, (name, s, ok) in enumerate(SCENARIOS):
            # 조건 순서를 번갈아 바꾼다: 같은 상황에서 늘 같은 모델이 먼저 불리지 않게 (#204 리뷰)
            order = CONDITIONS if (rep + si) % 2 == 0 else list(reversed(CONDITIONS))
            for c in order:
                r = call_once(*c, state(s))
                runs.append((c, name, r, r["pick"] in ok))
                k += 1
                raw.append({"seq": k, "rep": rep, "scenario": name, "model": c[0], "effort": c[1],
                            "sec": r["sec"], "pick": r["pick"], "hit": r["pick"] in ok})
    results = []
    for c in CONDITIONS:
        mine = [(name, r, hit) for cc, name, r, hit in runs if cc == c]
        secs = [r["sec"] for _, r, _ in mine]
        row = {"model": c[0], "effort": c[1], "calls": len(mine), "hits": sum(h for *_, h in mine),
               "mean_sec": round(statistics.mean(secs), 2), "p90_sec": p90(secs), "max_sec": max(secs),
               "cost_per_call": round(statistics.mean(r["cost"] for _, r, _ in mine), 5),
               "by_scenario": {name: [r["pick"] for nm, r, _ in mine if nm == name] for name, _, _ in SCENARIOS}}
        results.append(row)
        print(f"\n== {c[0]} effort={c[1]}: 규칙대로 {row['hits']}/{row['calls']}, 평균 {row['mean_sec']}초, "
              f"90% {row['p90_sec']}초, 최대 {row['max_sec']}초, 1회 ${row['cost_per_call']}")
        for name, picks in row["by_scenario"].items():
            print(f"   {name:<10} {', '.join(picks)}")
    path = ROOT / "logs" / "tutor_latency.json"
    path.write_text(json.dumps({"summary": results, "runs": raw}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {path}  /  전체 비용 ${sum(r['cost'] for *_, r, _ in runs):.4f}")


if __name__ == "__main__":
    main(sys.argv[1:])
