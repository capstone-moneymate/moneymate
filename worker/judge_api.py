"""판단 채점 FastAPI 서버 (A). Spring Boot 의 /api/judgement 가 이 서버를 HTTP로 부른다.

실행:
    cd worker
    uvicorn judge_api:app --port 8000          # 개발 중에는 --reload 를 붙인다
    docker compose up -d judge                 # 또는 레포 루트에서 컨테이너로

엔드포인트
- GET  /health  살아 있는지, 지금 어느 채점기를 쓰는지
- POST /judge   판단해보기 주관식 근거 1개를 채점한다

채점 함수 진입점
- generate/judge.py 의 grade() 가 있으면 그것을 부른다 (Claude 루브릭 채점, 실패하면 그 안에서 규칙 채점으로 전환).
- judge.py 가 아직 없으면 generate/rule_judge.py 의 grade() (키워드 규칙 채점)를 부른다.
- judge.grade() 가 예외를 올려도 이 서버가 규칙 채점으로 한 번 더 받아서, 채점 요청이 500 으로 끝나지 않게 한다.

이 서버는 DB를 읽지 않는다. 카드의 key_facts 와 개념 id(steps.answer 의 chain·counter)를 이름·별칭으로 풀어서
보내는 것은 부르는 쪽(Spring /api/judgement, #55 2차)의 몫이다. 하루 호출 제한·같은 답안 해시 재사용·실패 시
고정 문구도 Spring 몫이다.
Claude 호출 비용 기록과 월 한도 확인은 judge.py 가 C의 generate/llm_client.py 로 한다 (module='judge').
"""
import logging
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from generate import rule_judge

try:
    from generate import judge as _judge  # Claude 루브릭 채점 (#55)
except ModuleNotFoundError as e:
    # judge.py 파일이 없을 때만 규칙 채점으로 간다. judge.py 안의 import 오류(패키지 누락 등)는 그대로 올려서 드러낸다
    if e.name != "generate.judge":
        raise
    _judge = None

log = logging.getLogger("judge_api")

GRADER = "judge" if _judge is not None else "rule"
MAX_ANSWER_CHARS = 2000  # 근거 답안 최대 글자 수. 너무 긴 입력으로 Claude 비용이 커지는 것을 막는다


# ---------- 요청·응답 스키마 ----------

class KeyFact(BaseModel):
    """cards.key_facts 한 줄. keywords 중 하나라도 답안에 있으면 그 사실을 쓴 것으로 본다."""
    text: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)


class Concept(BaseModel):
    """concepts 테이블 한 행에서 이름과 별칭만."""
    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)


class JudgeRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=MAX_ANSWER_CHARS, description="사용자가 쓴 주관식 근거")
    key_facts: list[KeyFact] = Field(default_factory=list, description="카드의 key_facts (증거 채점용)")
    chain: list[Concept] = Field(default_factory=list, description="인과 경로 개념, 순서대로 (추론 채점용)")
    counter: list[Concept] = Field(default_factory=list, description="판단을 뒤집을 다른 힘 개념 (반박 채점용)")
    card_id: int | None = Field(default=None, description="llm_cost_log 의 문제별 비용 집계용")
    step_id: int | None = None


class Rubric(BaseModel):
    evidence: int = Field(ge=0, le=rule_judge.MAX["evidence"])
    reasoning: int = Field(ge=0, le=rule_judge.MAX["reasoning"])
    rebuttal: int = Field(ge=0, le=rule_judge.MAX["rebuttal"])


class JudgeResponse(BaseModel):
    rubric: Rubric
    total: int = Field(ge=0, le=rule_judge.TOTAL_MAX)
    score: int = Field(ge=0, le=100, description="100점 환산. 60점 이상이면 맞음 (conventions P17)")
    matched_facts: list[str]
    matched_concepts: list[str]
    grader: Literal["claude", "rule"] = Field(description="실제로 점수를 매긴 쪽")
    reasons: dict[str, str] = Field(default_factory=dict,
                                    description="Claude 채점 이유 {reasoning, rebuttal}. 규칙 채점이면 빈 객체")


class Health(BaseModel):
    status: Literal["ok"]
    grader: Literal["judge", "rule"] = Field(description="judge = judge.py 연결됨, rule = 규칙 채점만")


# ---------- 앱 ----------

app = FastAPI(title="moneymate judge", version="0.1.0")


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", grader=GRADER)


def _rule_grade(args: dict):
    return rule_judge.grade(args["text"], args["key_facts"], args["chain"], args["counter"])


@app.post("/judge", response_model=JudgeResponse)
def judge(req: JudgeRequest) -> JudgeResponse:
    args = {
        "text": req.answer,
        "key_facts": [f.model_dump() for f in req.key_facts],
        "chain": [c.model_dump() for c in req.chain],
        "counter": [c.model_dump() for c in req.counter],
    }
    grader = "rule"
    if _judge is not None:
        try:
            result = _judge.grade(**args, card_id=req.card_id)
            # judge.py 가 안에서 규칙 채점으로 넘어갔으면 grader="rule" 을 달아 준다
            grader = getattr(result, "grader", "claude")
        except Exception:  # noqa: BLE001 - 어떤 실패든 규칙 채점으로 받는다
            log.exception("judge.grade 실패, 규칙 채점으로 전환 (card_id=%s)", req.card_id)
            result = _rule_grade(args)
            grader = "rule"
    else:
        result = _rule_grade(args)

    return JudgeResponse(
        rubric=Rubric(**result.rubric),
        total=result.total,
        score=result.score,
        matched_facts=list(result.matched_facts),
        matched_concepts=list(result.matched_concepts),
        grader=grader,
        reasons=dict(getattr(result, "reasons", None) or {}),
    )
