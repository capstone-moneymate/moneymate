"""출제 에이전트 (기술확정안 "문제 생성·검증" 6·7·8단계).

사용 예:
    from generate.compose import compose
    result = compose(source, classify_result, card_date=date(2026, 11, 2))
    result.card_id   # 저장된 카드 id (검증을 끝내 통과 못 하면 None)

하는 일
1. 출제: Claude Sonnet 이 1차 자료와 유형·시작 개념을 받고 tools.py 도구를 스스로 불러 숫자·경로를 얻은 뒤
   카드뉴스·단계를 submit_card 도구로 낸다. tool use 루프는 직접 돌리고, API 호출은 MAX_CALLS 번까지만.
2. 검증·수정: 코드가 검사한다 (유형별 단계 순서, 개념 id, 인과 순서는 B의 validators, 차트 숫자는 다시 계산,
   보기·정답 번호, 금지 표현, key_facts). 실패하면 이유를 submit_card 의 결과로 돌려줘 고치게 하고, 최대 MAX_REPAIRS 번.
   통과 여부는 코드가 정한다. 검토 에이전트(독립 풀이)는 담당이 정해지면 review 인자로 붙인다.
3. 저장: 통과하면 cards(status='pending')·card_sources·steps 에 넣고, 이 카드를 만든 compose 호출의
   llm_cost_log 행에 card_id 를 붙인다 (문제 1개당 비용 집계용).
"""
import json
import random
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from db import get_conn
from generate import tools
from generate.classify import ClassifyResult, Concept, load_concepts
from generate.llm_client import SONNET, cost_usd, create
from validate.validators import verify

PROMPT = (Path(__file__).parent / "prompts" / "compose.md").read_text(encoding="utf-8")
MAX_CALLS = 15  # 출제 1건에 쓰는 Sonnet 호출 상한 (수정 포함)
MAX_REPAIRS = 3  # 검증 실패 후 고쳐 쓰기 상한 (기술확정안)
STEP_ORDER = {
    1: ["concept", "quiz", "chart", "judgement"],
    2: ["concept", "quiz", "causal_order", "chart", "judgement"],
    3: ["concept", "judgement"],
}
# 매수·매도 권유, 수익 예측. 걸린 표현은 계속 추가한다 (B의 금지 표현 검증기가 생기면 그쪽으로 옮긴다)
FORBIDDEN = re.compile(
    r"매수\s*(?:추천|하세요|하라|타이밍)|매도\s*(?:추천|하세요|하라|타이밍)|사세요|파세요|팔아라|사라\b|담으세요|담아라"
    r"|추천\s*종목|목표\s*(?:주)?가|오를\s*것|내릴\s*것|떨어질\s*것|상승할\s*(?:것|전망)|하락할\s*(?:것|전망)"
    r"|수익(?:이|을)?\s*(?:기대|보장)|반드시\s*오"
)


class ComposeError(RuntimeError):
    pass


@dataclass
class ComposeResult:
    card_id: int | None
    card: dict | None
    errors: list[str]  # 마지막 검증 실패 이유 (통과하면 빈 목록)
    calls: int = 0
    repairs: int = 0
    cost_usd: float = 0.0
    request_ids: list[str] = field(default_factory=list)


# --- 카드 스키마 (submit_card 입력) ---

def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def card_schema() -> dict:
    # 개념 id 는 문자열로 받고 사전에 있는지는 validate_card 가 확인한다
    cid = {"type": "string"}
    ids = {"type": "array", "items": cid}
    text = {"type": "string"}
    texts = {"type": "array", "items": text}

    def step(kind: str, props: dict) -> dict:
        return _obj({"kind": {"type": "string", "const": kind}, "concept_ids": ids, **props})

    return _obj({
        "title": text,
        "slides": {"type": "array", "items": _obj({
            "label": text, "heading": text, "body": text,
            "facts": {"type": "array", "items": _obj({"label": text, "value": text})},
        })},
        "key_facts": {"type": "array", "items": _obj({"text": text, "keywords": texts})},
        "steps": {"type": "array", "items": {"anyOf": [
            step("concept", {"title": text, "body": text,
                             "terms": {"type": "array", "items": _obj({"term": text, "desc": text})}}),
            step("quiz", {"question": text, "options": texts, "answer_index": {"type": "integer"},
                          "explanation": text}),
            step("causal_order", {
                "question": text,
                "items": {"type": "array", "items": _obj({"concept_id": cid, "label": text})},
                "causal": _obj({"start_concept": cid, "change": {"type": "string", "enum": ["up", "down"]},
                                "end_concept": cid, "answer_order": ids,
                                "direction": {"type": "string", "enum": ["up", "down"]}, "evidence_quote": text}),
                "explanation": text,
            }),
            step("chart", {
                "question": text, "ticker": text, "options": texts, "answer_index": {"type": "integer"},
                "explanation": text,
                "chart_check": _obj({"metric": {"type": "string", "enum": list(tools.METRICS)},
                                     "start_date": {"type": ["string", "null"]}, "end_date": text, "value": text}),
            }),
            step("judgement", {"question": text, "context": text, "choices": texts, "chain": ids, "counter": ids}),
        ]}},
    })


# --- 입력 만들기 ---

def build_system(concepts: list[Concept]) -> str:
    """프롬프트 + 개념 사전. 사전은 매번 같아서 캐시된다."""
    lines = [PROMPT, "", "## 개념 사전 (concept_ids 에는 이 id 만. id | 이름 | 테마)"]
    lines += [f"{c.id} | {c.name} | {c.theme}" for c in concepts]
    return "\n".join(lines)


def source_text(source: dict) -> str:
    """에이전트에게 주는 원문. 검증기가 evidence_quote 를 이 글과 대조한다."""
    numbers = source.get("numbers") or {}
    lines = [source["title"]]
    lines += [f"{k}: {v}" for k, v in numbers.items()]
    return "\n".join(lines)


def build_user(source: dict, cls: ClassifyResult, etf_rows: list[dict]) -> str:
    lines = [
        f"유형: {cls.card_type}  (단계: {' → '.join(STEP_ORDER[cls.card_type])})",
        f"시작 개념: {cls.start_concept or '없음'}",
        f"분류: {source.get('category') or '-'}",
        f"회사·기관: {source.get('issuer_name') or '-'}",
        f"종목(차트·도구에 쓸 티커): {source.get('ticker') or '-'}",
        f"발표일: {source.get('published_date') or '-'}",
        "",
        "원문 (evidence_quote 는 이 안의 문장을 그대로):",
        source_text(source),
    ]
    if etf_rows:
        lines += ["", "액티브 ETF 보유 변화 (유형 3 판단해보기 context 에 쓴다. 숫자는 그대로):"]
        lines += [json.dumps(r, ensure_ascii=False, default=str) for r in etf_rows]
    return "\n".join(lines)


def load_etf_rows(ticker: str | None) -> list[dict]:
    """그 종목을 담은 ETF 마다 최신 스냅샷의 수량 변화. DB 가 없으면 빈 목록."""
    if not ticker:
        return []
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT h.etf_code, h.snapshot_date, h.shares, h.trend_chg_pct, h.day_chg_pct
                   FROM holdings_etf h
                   JOIN (SELECT etf_code, max(snapshot_date) AS d FROM holdings_etf GROUP BY etf_code) m
                     ON h.etf_code = m.etf_code AND h.snapshot_date = m.d
                   WHERE h.ticker = %s ORDER BY h.etf_code""",
                (ticker,),
            ).fetchall()
    except psycopg.Error:
        return []
    keys = ("etf_code", "snapshot_date", "shares", "trend_chg_pct", "day_chg_pct")
    return [dict(zip(keys, r)) for r in rows]


# --- 에이전트 루프 ---

# 카드는 submit_card 도구로 받는다. 카드 스키마를 구조화 출력(output_config.format)으로 걸면
# "compiled grammar is too large"(400)라서, 이 도구만 strict 를 끄고 모양은 코드(shape_errors)가 확인한다.
SUBMIT = "submit_card"


def submit_tool() -> dict:
    return {
        "name": SUBMIT,
        "description": "완성한 카드를 낸다. 코드 검증을 통과하면 끝나고, 실패하면 이유가 오류로 돌아오니 고쳐서 다시 낸다.",
        "input_schema": card_schema(),
    }


@dataclass
class _Run:
    messages: list
    system: str
    ctx: tools.ToolContext
    result: ComposeResult
    submit_id: str | None = None  # 마지막 submit_card 호출 id (검증 결과를 이 id 로 돌려준다)
    pending: list = field(default_factory=list)  # submit_card 와 같이 부른 다른 도구의 결과


def _tool_results(blocks, ctx) -> list[dict]:
    out = []
    for b in blocks:
        content, is_error = tools.run_tool(b.name, b.input, ctx)
        out.append({"type": "tool_result", "tool_use_id": b.id, "content": content, "is_error": is_error})
    return out


def _next_card(run: _Run) -> dict:
    """submit_card 가 올 때까지 호출하고 그 입력(카드)을 돌려준다. 호출 상한을 넘으면 ComposeError."""
    while run.result.calls < MAX_CALLS:
        resp = create(
            "compose",
            note=f"source={run.ctx.ref}",
            model=SONNET,
            max_tokens=16000,
            system=run.system,
            tools=tools.TOOLS + [submit_tool()],
            messages=run.messages,
            cache_control={"type": "ephemeral"},  # 도구·시스템·앞선 대화를 캐시 (루프마다 다시 보내므로)
            output_config={"effort": "medium"},
        )
        run.result.calls += 1
        run.result.cost_usd += cost_usd(SONNET, resp.usage)
        run.result.request_ids.append(resp._request_id)
        run.messages.append({"role": "assistant", "content": resp.content})  # thinking 블록까지 그대로 돌려준다

        uses = [b for b in resp.content if b.type == "tool_use"]
        submits = [b for b in uses if b.name == SUBMIT]
        others = [b for b in uses if b.name != SUBMIT]
        if submits:
            run.pending = _tool_results(others, run.ctx)
            run.submit_id = submits[-1].id
            # 같은 턴에 submit_card 를 두 번 불렀으면 앞의 것은 무시했다고 알려 준다
            run.pending += [{"type": "tool_result", "tool_use_id": b.id, "content": "마지막 제출만 봐요",
                             "is_error": True} for b in submits[:-1]]
            return submits[-1].input
        if resp.stop_reason == "tool_use":
            run.messages.append({"role": "user", "content": _tool_results(others, run.ctx)})  # 병렬 호출 결과는 한 메시지에
            continue
        if resp.stop_reason == "end_turn":
            run.messages.append({"role": "user", "content": f"카드는 {SUBMIT} 도구로 내 주세요."})
            continue
        raise ComposeError(f"출제 응답이 끝나지 않았어요: stop_reason={resp.stop_reason}")
    raise ComposeError(f"호출 상한 {MAX_CALLS}회를 넘었어요")


def _send_back(run: _Run, errors: list[str]) -> None:
    """검증 실패 이유를 submit_card 의 결과로 돌려준다."""
    text = "검증에서 아래 문제가 나왔어요. 고친 카드 전체를 다시 내 주세요.\n- " + "\n- ".join(errors)
    run.messages.append({"role": "user", "content": run.pending + [
        {"type": "tool_result", "tool_use_id": run.submit_id, "content": text, "is_error": True}]})
    run.pending = []


# --- 검증 (코드가 통과 여부를 정한다) ---

def _strings(x) -> list[str]:
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        return [s for v in x.values() for s in _strings(v)]
    if isinstance(x, list):
        return [s for v in x for s in _strings(v)]
    return []


_PY = {"string": str, "integer": int, "array": list, "object": dict, "null": type(None)}


def shape_errors(value, schema: dict, path: str = "card") -> list[str]:
    """card_schema 모양 확인 (submit_card 가 strict 가 아니어서). 필드 빠짐·타입·const·enum 만 본다."""
    if "anyOf" in schema:
        options = schema["anyOf"]
        if isinstance(value, dict) and "kind" in value:  # 단계는 kind 로 맞는 모양을 고른다
            options = [o for o in options if o.get("properties", {}).get("kind", {}).get("const") == value["kind"]]
        if not options:
            return [f"{path}: 알 수 없는 kind {value.get('kind')}"]
        found = [shape_errors(value, o, path) for o in options]
        return min(found, key=len)
    types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    if not any(isinstance(value, _PY[t]) and not (t == "integer" and isinstance(value, bool)) for t in types):
        return [f"{path}: {'/'.join(types)} 이어야 해요"]
    if "const" in schema and value != schema["const"]:
        return [f"{path}: {schema['const']} 이어야 해요"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: {', '.join(map(str, schema['enum']))} 중 하나여야 해요"]
    errors = []
    if isinstance(value, dict):
        errors += [f"{path}.{k}: 빠졌어요" for k in schema.get("required", []) if k not in value]
        errors += [e for k, sub in schema.get("properties", {}).items() if k in value
                   for e in shape_errors(value[k], sub, f"{path}.{k}")]
    if isinstance(value, list) and "items" in schema:
        errors += [e for i, v in enumerate(value) for e in shape_errors(v, schema["items"], f"{path}[{i}]")]
    return errors


# 연도가 있으면 -./ 모두, 연도가 없으면 '/' 와 'M월 D일'만 날짜로 본다 ('3.0', '16.48' 은 숫자)
_DATE = re.compile(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})|(\d{1,2})/(\d{1,2})|(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_NUM = re.compile(r"[+\-−]?\d+(?:,\d{3})*(?:\.\d+)?")


def _dates_in(text: str) -> list[tuple[int | None, int, int]]:
    """보기 문장 속 날짜 (연, 월, 일). '2026-10-30', '10/30', '10월 30일' 모두 읽는다."""
    out = []
    for m in _DATE.finditer(text):
        if m.group(1):
            out.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
        elif m.group(4):
            out.append((None, int(m.group(4)), int(m.group(5))))
        else:
            out.append((None, int(m.group(6)), int(m.group(7))))
    return out


def _numbers_in(text: str) -> list[tuple[float, float]]:
    """보기 문장 속 숫자와 그 표기의 허용 오차. '약 +16.5%'는 소수 한 자리라 ±0.05, '3배'는 ±0.5.
    날짜 안의 숫자(2026-10-30 의 -10 등)는 빼고 읽는다."""
    text = _DATE.sub(" ", text)
    out = []
    for raw in _NUM.findall(text):
        s = raw.replace(",", "").replace("−", "-")
        decimals = len(s.split(".")[1]) if "." in s else 0
        out.append((float(s), max(tools.TOLERANCE, 0.5 * 10 ** -decimals)))
    return out


def option_matches(option: str, metric: str, expected) -> bool:
    """보기 문장에 코드가 계산한 값이 들어 있는가. 표기('3'/'3.0'/'3배', '10월 30일')가 달라도 숫자로 비교한다."""
    if metric == "top_volume_date":
        y, m, d = map(int, str(expected).split("-"))
        return any((oy is None or oy == y) and (om, od) == (m, d) for oy, om, od in _dates_in(option))
    return any(abs(v - float(expected)) <= tol for v, tol in _numbers_in(option))


def option_errors(options: list[str], answer_index: int, metric: str, expected) -> list[str]:
    """정답 보기에 확인한 값이 있고, 다른 보기에는 없어야 한다 (정답이 하나로 읽히게)."""
    hits = [i for i, o in enumerate(options) if option_matches(o, metric, expected)]
    if answer_index not in hits:
        return [f"정답 보기({answer_index}번 '{options[answer_index]}')에 코드가 확인한 값 {expected} 이 없어요. "
                "answer_index 나 보기 문장을 고치세요"]
    if len(hits) > 1:
        return [f"확인한 값 {expected} 이 보기 여러 개({', '.join(map(str, hits))}번)에 들어 있어 정답이 하나로 읽히지 않아요"]
    return []


def validate_card(card: dict, card_type: int, concept_ids: set[str], ctx: tools.ToolContext) -> list[str]:
    errors = shape_errors(card, card_schema())
    if errors:
        return errors[:10]  # 모양이 틀리면 내용 검사는 하지 않는다
    errors = []
    steps = card.get("steps", [])
    kinds = [s["kind"] for s in steps]
    if kinds != STEP_ORDER[card_type]:
        errors.append(f"유형 {card_type} 단계 순서는 {' → '.join(STEP_ORDER[card_type])} 이어야 해요 (지금 {' → '.join(kinds)})")
    if not 2 <= len(card.get("slides", [])) <= 3:
        errors.append("카드뉴스는 2~3장이어야 해요")
    facts = card.get("key_facts", [])
    if not 2 <= len(facts) <= 4 or any(not f["keywords"] for f in facts):
        errors.append("key_facts 는 2~4개이고 각각 keywords 가 1개 이상 있어야 해요")

    hits = sorted({m.group(0) for s in _strings(card) for m in FORBIDDEN.finditer(s)})
    if hits:
        errors.append(f"매수·매도 권유나 예측 표현이 있어요: {', '.join(hits)}")

    for no, s in enumerate(steps, 1):
        where = f"{no}단계({s['kind']})"
        unknown = sorted(set(s["concept_ids"]) - concept_ids)
        if unknown:
            errors.append(f"{where}: 사전에 없는 개념 {', '.join(unknown)}")
        if s["kind"] in ("quiz", "chart"):
            n = len(s["options"])
            if not 2 <= n <= 4:
                errors.append(f"{where}: 보기는 2~4개여야 해요")
            if not 0 <= s["answer_index"] < n:
                errors.append(f"{where}: answer_index {s['answer_index']} 가 보기 범위 밖이에요")
        if s["kind"] == "causal_order":
            c = s["causal"]
            report = verify(c, ctx.source_text)
            errors += [f"{where}: {e}" for e in report.errors]
            if sorted(i["concept_id"] for i in s["items"]) != sorted(c["answer_order"]):
                errors.append(f"{where}: items 개념과 정답 순서 개념이 달라요")
            if s["concept_ids"] != c["answer_order"]:
                errors.append(f"{where}: concept_ids 는 정답 순서 그대로여야 해요")
        if s["kind"] == "chart":
            try:
                out = tools.validate_chart_answer(ticker=s["ticker"], **s["chart_check"])
                if not out["passed"]:
                    errors.append(f"{where}: {out['error']}")
                elif 0 <= s["answer_index"] < len(s["options"]):
                    errors += [f"{where}: {e}" for e in option_errors(s["options"], s["answer_index"],
                                                                       out["metric"], out["expected"])]
            except tools.ToolError as e:
                errors.append(f"{where}: 차트 정답을 확인할 수 없어요 ({e})")
            except psycopg.Error:
                errors.append(f"{where}: 가격 DB 에 연결하지 못해 차트 정답을 확인할 수 없어요")
        if s["kind"] == "judgement":
            if not 2 <= len(s["choices"]) <= 3:
                errors.append(f"{where}: choices 는 2~3개여야 해요")
            if card_type == 2 and not s["chain"]:
                errors.append(f"{where}: 유형 2는 chain(근거 인과 경로)이 있어야 해요")
    return errors


# --- DB 행으로 바꾸기 ---

def _shuffled(items: list[dict], answer: list[str], seed: str) -> list[dict]:
    """정답 순서와 다르게 섞는다. 같은 자료면 늘 같은 순서 (재현용)."""
    out = list(items)
    random.Random(seed).shuffle(out)
    if len(out) > 1 and [i["concept_id"] for i in out] == answer:
        out = out[1:] + out[:1]
    return out


def step_rows(card: dict, seed: str) -> list[dict]:
    """steps 테이블 행 (content 는 화면에 내려보내는 부분, answer 는 서버만 보는 정답)."""
    rows = []
    for no, s in enumerate(card["steps"], 1):
        kind, content, answer = s["kind"], {"concept_ids": s["concept_ids"]}, None
        if kind == "concept":
            content |= {"title": s["title"], "body": s["body"], "terms": s["terms"]}
        elif kind in ("quiz", "chart"):
            content |= {"question": s["question"], "options": s["options"]}
            if kind == "chart":
                content["ticker"] = s["ticker"]
            answer = {"correct": s["answer_index"], "explanation": s["explanation"]}
            if kind == "chart":
                answer["check"] = s["chart_check"]
        elif kind == "causal_order":
            c = s["causal"]
            content |= {"question": s["question"], "items": _shuffled(s["items"], c["answer_order"], seed)}
            answer = {"correct": c["answer_order"], "explanation": s["explanation"], "change": c["change"],
                      "direction": c["direction"], "evidence_quote": c["evidence_quote"]}
        elif kind == "judgement":
            content |= {"question": s["question"], "context": s["context"], "choices": s["choices"]}
            answer = {"chain": s["chain"], "counter": s["counter"]}  # A의 채점이 경로·반박 개념으로 쓴다
        rows.append({"step_no": no, "kind": kind, "content": content, "answer": answer})
    return rows


def save_pending(card: dict, cls: ClassifyResult, source: dict, card_date: date, result: ComposeResult) -> int:
    ticker = source.get("ticker") if cls.card_type == 3 else None
    links = [{"name": source.get("issuer_name") or source.get("source_type"), "url": source["url"],
              "published_date": str(source.get("published_date"))}]
    model_info = {"model": SONNET, "calls": result.calls, "repairs": result.repairs,
                  "cost_usd": round(result.cost_usd, 6)}
    with get_conn() as conn:
        card_id = conn.execute(
            """INSERT INTO cards (card_date, card_type, status, title, slides, start_concept, ticker,
                                  key_facts, source_links, model_info)
               VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (card_date, cls.card_type, card["title"], Jsonb(card["slides"]), cls.start_concept, ticker,
             Jsonb(card["key_facts"]), Jsonb(links), Jsonb(model_info)),
        ).fetchone()[0]
        conn.execute("INSERT INTO card_sources (card_id, source_id, is_main) VALUES (%s, %s, true)",
                     (card_id, source["id"]))
        for r in step_rows(card, seed=str(source.get("source_key") or source["id"])):
            conn.execute("INSERT INTO steps (card_id, step_no, kind, content, answer) VALUES (%s, %s, %s, %s, %s)",
                         (card_id, r["step_no"], r["kind"], Jsonb(r["content"]),
                          Jsonb(r["answer"]) if r["answer"] is not None else None))
        # 이 카드를 만든 호출의 비용 로그에 card_id 를 붙인다 (llm_client 가 note 맨 앞에 request_id 를 쓴다)
        for rid in result.request_ids:
            conn.execute("UPDATE llm_cost_log SET card_id = %s WHERE note LIKE %s", (card_id, f"request_id={rid}%"))
    return card_id


# --- 실행 ---

def compose(source: dict, cls: ClassifyResult, card_date: date, concepts: list[Concept] | None = None,
            save: bool = True, review=None) -> ComposeResult:
    """source: raw_sources 한 행 (id, source_type, source_key, title, url, category, issuer_name, ticker,
    published_date, numbers). review: (card) -> 실패 이유 목록. 검토 에이전트가 생기면 넘긴다."""
    concepts = concepts or load_concepts()
    ids = [c.id for c in concepts]
    ref = f"{source.get('source_type')}:{source.get('source_key')}"
    run = _Run(
        messages=[{"role": "user", "content": build_user(source, cls, load_etf_rows(source.get("ticker")))}],
        system=build_system(concepts),
        ctx=tools.ToolContext(source_text=source_text(source), ref=ref),
        result=ComposeResult(card_id=None, card=None, errors=[]),
    )
    res = run.result
    try:
        card = _next_card(run)
        while True:
            errors = validate_card(card, cls.card_type, set(ids), run.ctx)
            if not errors and review:
                errors = review(card)
            res.card, res.errors = card, errors
            if not errors or res.repairs >= MAX_REPAIRS:
                break
            res.repairs += 1
            _send_back(run, errors)
            card = _next_card(run)
    except ComposeError as e:
        res.errors = [str(e)]
    if save and res.card and not res.errors:
        res.card_id = save_pending(res.card, cls, source, card_date, res)
    return res
