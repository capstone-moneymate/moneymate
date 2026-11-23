"""학습자 상태 API (사람2, 계획 2-3). 채점 서버(judge_api.py)에 붙는 라우터다.
Spring 이 본 문제(퀴즈·차트 읽기·인과 순서)를 채점한 뒤 여기를 불러 알 확률(BKT)을 고친다.

- POST /learner/answer            답 하나를 그 단계의 인과 사전 개념마다 반영 (learner/state.update_causal)
- GET  /learner/mastery/{user_id} 개념별 알 확률 (learner/state.get_mastery)

찍어서 맞힐 확률은 문제 형식에서 여기서 계산한다 (guess_for_step). Spring 은 형식과 개수만 보낸다.
채점은 하지 않는다. 정답 여부는 채점한 쪽(Spring)이 넘긴다.
"""
import math
from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from learner import state

router = APIRouter(prefix="/learner", tags=["learner"])


def guess_for_step(kind: str, count: int) -> float:
    """본 문제를 찍어서 맞힐 확률.
    보기 고르기(quiz, chart): 1 / 보기 수 (4지선다 0.25)
    인과 순서(causal_order): 1 / 개념 수! (개념 3개를 순서대로 놓기 = 1/6)"""
    if count < 1:
        raise ValueError(f"개수는 1 이상이어야 해요: {count}")
    if kind in ("quiz", "chart"):
        return 1 / count
    if kind == "causal_order":
        return 1 / math.factorial(count)
    raise ValueError(f"찍어서 맞힐 확률을 모르는 형식이에요: {kind}")


class AnswerIn(BaseModel):
    user_id: UUID
    concept_ids: list[str] = Field(description="그 단계의 인과 사전 개념 id (steps.content.concept_ids)")
    correct: bool
    kind: Literal["quiz", "chart", "causal_order"]
    count: int = Field(ge=1, le=20, description="quiz·chart 는 보기 수, causal_order 는 놓을 개념 수")


class AnswerOut(BaseModel):
    guess_p: float
    mastery: dict[str, float] = Field(description="{인과 사전 id: 새 알 확률}. 사전에 없는 id 는 빠진다")


class MasteryOut(BaseModel):
    mastery: dict[str, float] = Field(description="{개념 이름: 알 확률}. 안 풀어 본 개념은 처음 값")


def _conn():
    # psycopg 를 여기서 불러온다. judge_api 를 띄우는 것만으로는 DB 가 필요 없게 (채점 테스트는 DB 없이 돈다)
    from db import get_conn

    return get_conn()


@router.post("/answer", response_model=AnswerOut)
def record_answer(req: AnswerIn) -> AnswerOut:
    guess = guess_for_step(req.kind, req.count)
    with _conn() as conn:
        mastery = state.update_causal(conn, str(req.user_id), req.concept_ids, req.correct, guess)
    return AnswerOut(guess_p=guess, mastery=mastery)


@router.get("/mastery/{user_id}", response_model=MasteryOut)
def read_mastery(user_id: UUID) -> MasteryOut:
    with _conn() as conn:
        return MasteryOut(mastery=state.get_mastery(conn, str(user_id)))
