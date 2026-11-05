"""판단 근거 Claude 루브릭 채점 + AI 분석 피드백 (A, #55·#56). judge_api.py 의 /judge 가 부른다.

사용 예:
    from generate.judge import grade
    r = grade(answer_text, key_facts=card["key_facts"], chain=[{"name": ..., "aliases": [...]}, ...],
              counter=[...], card_id=12)
    r.rubric    # {"evidence": 2, "reasoning": 3, "rebuttal": 1}
    r.score     # 67
    r.grader    # "claude" 또는 "rule" (Claude 실패로 규칙 채점을 썼을 때)
    r.feedback  # {"good": ..., "think_more": ..., "chain": [{"name": ..., "used": True}, ...], "chain_comment": ...}

나눠 맡는 것 (기술확정안 "채점", Claude 호출은 답안당 1번)
- 증거 0~2: 코드. rule_judge.score_evidence 가 key_facts 와 대조한다. 결과(점수·찾은 사실·찾은 개념)를 Claude 에게 넘긴다
- 추론 0~4, 반박 0~3, 피드백 문장(잘한 점·더 생각할 점·인과 뼈대 설명): Claude Sonnet 이 한 JSON 으로
- 범위 자르기·합계·100점 환산: 코드. Claude 가 준 점수는 0~배점으로 자르고 총점은 합계로 계산한다
- 인과 뼈대 경로: 코드. 카드의 chain 개념 순서 + 사용자가 그 개념을 썼는지(used)

실패하면 (같은 함수 안에서) rule_judge.grade 로 전환하고 피드백은 고정 문구로 채운다 (fallback_feedback):
API 오류·연결 오류, 월 한도 초과(BudgetExceeded), 응답이 끝나지 않음, JSON 파싱·필드 오류.

이유·피드백 문장에 금지 표현(B의 validators.find_banned, 목록은 validate/banned_terms.txt)이 있으면
그 항목만 고정 문구로 바꾼다. 비용은 llm_client 가 llm_cost_log 에 module='judge' 로 남긴다.
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from generate import rule_judge
from generate.llm_client import SONNET, create, text_of
from validate.validators import find_banned

log = logging.getLogger(__name__)

PROMPT = (Path(__file__).parent / "prompts" / "judge.md").read_text(encoding="utf-8")
MODEL = SONNET
EFFORT = "low"  # 사용자가 결과 화면을 기다리므로 짧게. κ(8주차)가 낮으면 올려 본다
MAX_TOKENS = 2048
# 기술확정안 "루브릭": 피드백 문장에 금지 표현이 있으면 고정 문구로 대체
FIXED_GOOD = "근거 있는 선택이었어요."
FIXED_THINK_MORE = "이런 경우도 생길 수 있어요."
FIXED_REASON = f"{FIXED_GOOD} {FIXED_THINK_MORE}"
LLM_KEYS = ("reasoning", "rebuttal")  # Claude 가 매기는 기준
TEXT_KEYS = ("reasoning_reason", "rebuttal_reason", "good", "think_more", "chain_comment")


@dataclass(frozen=True)
class JudgeResult:
    rubric: dict[str, int]
    total: int
    score: int  # 0~100
    matched_facts: list[str]
    matched_concepts: list[str]
    grader: str  # "claude" | "rule"
    reasons: dict[str, str] = field(default_factory=dict)  # {"reasoning": "...", "rebuttal": "..."}, 규칙 채점이면 빈 dict
    feedback: dict = field(default_factory=dict)  # 잘한 점·더 생각할 점·인과 뼈대 (build_feedback / fallback_feedback)
    error: str | None = None  # 규칙 채점으로 넘어간 이유 (로그·일괄 채점 CSV 용)


def clip(value, key: str) -> int:
    """0~배점으로 자른다. 정수가 아니면 ValueError (규칙 채점으로 전환된다)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        raise ValueError(f"{key} 점수가 정수가 아니에요: {value!r}")
    return max(0, min(rule_judge.MAX[key], int(value)))


def clean_text(text, fixed: str = FIXED_REASON) -> str:
    """금지 표현이 있으면 고정 문구로 바꾼다. 문자열이 아니면 ValueError (규칙 채점으로 전환된다)."""
    if not isinstance(text, str):
        raise ValueError(f"문장이 아니에요: {text!r}")
    text = text.strip()
    return fixed if find_banned([text]) else text


clean_reason = clean_text  # 이전 이름 (#55)


def chain_path(chain: list[dict], matched_concepts: list[str]) -> list[dict]:
    """인과 뼈대 경로. 카드의 chain 순서 그대로, 사용자가 그 개념을 썼으면 used=True (코드가 정한다)."""
    used = set(matched_concepts)
    return [{"name": c["name"], "used": c["name"] in used} for c in chain]


def fallback_comment(path: list[dict]) -> str:
    """Claude 없이 쓰는 인과 뼈대 설명. 안 쓴 개념이 있으면 그 개념을 짚는다."""
    if not path:
        return ""
    missing = [p["name"] for p in path if not p["used"]]
    if not missing:
        return "인과 뼈대의 개념을 모두 이어서 썼어요."
    return f"{', '.join(missing)}까지 이어 보면 인과 뼈대가 완성돼요."


def fallback_feedback(chain: list[dict], matched_concepts: list[str]) -> dict:
    """Claude 를 못 쓸 때의 피드백: 문장은 고정 문구, 인과 뼈대 경로는 코드 값 그대로."""
    path = chain_path(chain, matched_concepts)
    return {"good": FIXED_GOOD, "think_more": FIXED_THINK_MORE, "chain": path,
            "chain_comment": fallback_comment(path)}


def output_schema() -> dict:
    # 범위(minimum·maximum)·글자 수는 스키마에 넣지 않는다. 점수는 코드가 자르고, 글자 수는 프롬프트로 안내한다
    props = {k: {"type": "integer"} for k in LLM_KEYS}
    props.update({k: {"type": "string"} for k in TEXT_KEYS})
    return {
        "type": "object",
        "properties": props,
        "required": [*LLM_KEYS, *TEXT_KEYS],
        "additionalProperties": False,
    }


def build_user(text: str, key_facts: list[dict], chain: list[dict], counter: list[dict],
               evidence: int = 0, matched_facts: list[str] | None = None,
               matched_concepts: list[str] | None = None) -> str:
    """답안과 코드 채점 결과를 JSON 데이터로 감싸 넘긴다 (답안 속 지시문이 프롬프트처럼 읽히지 않게)."""
    data = {
        "answer": text,
        "chain": [{"name": c["name"], "aliases": c.get("aliases", [])} for c in chain],
        "counter": [{"name": c["name"], "aliases": c.get("aliases", [])} for c in counter],
        "key_facts": [f["text"] for f in key_facts],
        "code_result": {
            "evidence": evidence,
            "evidence_max": rule_judge.MAX["evidence"],
            "matched_facts": matched_facts or [],
            "matched_concepts": matched_concepts or [],
        },
    }
    return "<data>\n" + json.dumps(data, ensure_ascii=False) + "\n</data>"


def ask_claude(text: str, key_facts: list[dict], chain: list[dict], counter: list[dict],
               card_id: int | None = None, rule: rule_judge.RuleResult | None = None) -> dict:
    """Sonnet 1회 호출. 파싱만 하고 자르기·합계·금지 표현은 grade 가 한다."""
    rule = rule or rule_judge.grade(text, key_facts, chain, counter)
    resp = create(
        "judge",
        card_id=card_id,
        model=MODEL,
        max_tokens=MAX_TOKENS,
        # 루브릭 프롬프트는 매번 같아서 캐시한다
        system=[{"type": "text", "text": PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": build_user(
            text, key_facts, chain, counter,
            rule.rubric["evidence"], rule.matched_facts, rule.matched_concepts)}],
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": output_schema()}},
    )
    if resp.stop_reason != "end_turn":
        raise RuntimeError(f"judge 응답이 끝나지 않았어요: stop_reason={resp.stop_reason}")
    data = json.loads(text_of(resp))
    if not isinstance(data, dict):
        raise ValueError("judge 응답이 JSON 객체가 아니에요")
    return data


def grade(text: str, key_facts: list[dict], chain: list[dict], counter: list[dict] | None = None,
          card_id: int | None = None) -> JudgeResult:
    counter = counter or []
    rule = rule_judge.grade(text, key_facts, chain, counter)  # 증거 점수와 규칙 채점 대체값

    try:
        data = ask_claude(text, key_facts, chain, counter, card_id, rule)
        llm = {k: clip(data[k], k) for k in LLM_KEYS}
        reasons = {k: clean_text(data[f"{k}_reason"]) for k in LLM_KEYS}
        path = chain_path(chain, rule.matched_concepts)
        feedback = {
            "good": clean_text(data["good"], FIXED_GOOD),
            "think_more": clean_text(data["think_more"], FIXED_THINK_MORE),
            "chain": path,
            # 설명 문장에 금지 표현이 있으면 코드가 만든 설명으로 바꾼다
            "chain_comment": clean_text(data["chain_comment"], fallback_comment(path)),
        }
    except Exception as e:  # noqa: BLE001 - 어떤 실패든 규칙 채점으로 받는다 (기술확정안 "대체 수단")
        log.warning("Claude 채점 실패, 규칙 채점으로 전환 (card_id=%s): %s: %s",
                    card_id, e.__class__.__name__, e)
        return JudgeResult(rule.rubric, rule.total, rule.score, rule.matched_facts, rule.matched_concepts,
                           grader="rule", feedback=fallback_feedback(chain, rule.matched_concepts),
                           error=f"{e.__class__.__name__}: {e}")

    rubric = {"evidence": rule.rubric["evidence"], **llm}
    total = sum(rubric.values())  # Claude 가 준 총점은 받지도 믿지도 않는다
    return JudgeResult(rubric, total, rule_judge.to_score(total), rule.matched_facts, rule.matched_concepts,
                       grader="claude", reasons=reasons, feedback=feedback)
