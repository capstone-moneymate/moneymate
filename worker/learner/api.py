"""학습자 상태 API (사람2, 계획 2-3·2-4). 채점 서버(judge_api.py)에 붙는 라우터다.
Spring 이 본 문제(퀴즈·차트 읽기·인과 순서)를 채점한 뒤 여기를 불러 알 확률(BKT)과 복습 일정(FSRS)을 고친다.

- POST /learner/answer            답 하나를 그 단계의 인과 사전 개념마다 반영 (learner/state.update_causal)
- GET  /learner/mastery/{user_id} 개념별 알 확률 (learner/state.get_mastery)
- GET  /learner/reviews/{user_id} 오늘 복습할 개념 (learner/state.due_reviews)
- GET  /learner/calibration/{user_id} 확신 보정 2 × 2 표와 지표 (learner/state.calibration_report)
- POST /learner/review/quiz      오늘 복습할 개념의 새 문제 하나 (learner/review.prepare·save, 출제는 tutor/quiz.py)
- POST /learner/review/answer    복습 문제의 답을 채점하고 알 확률·복습 일정에 반영 (learner/review.answer)

찍어서 맞힐 확률은 문제 형식에서 여기서 계산한다 (guess_for_step). Spring 은 형식과 개수만 보낸다.
본 문제는 채점하지 않는다. 정답 여부는 채점한 쪽(Spring)이 넘긴다. 복습 문제만 여기서 내고 채점한다 (정답을 여기서 보관하므로).
"""
import logging
import math
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from learner import review, state

log = logging.getLogger(__name__)

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
    # 아래 셋은 복습 일정(FSRS 자동 평가)용. 화면이 안 보냈으면 null
    confidence: Literal[1, 2] | None = Field(default=None, description="1 헷갈려요, 2 확실해요")
    response_ms: int | None = Field(default=None, ge=0, description="문제가 뜬 순간부터 낼 때까지 (ms)")
    answer_changes: int | None = Field(default=None, ge=0, description="내기 전에 답을 바꾼 횟수")


class AnswerOut(BaseModel):
    guess_p: float
    mastery: dict[str, float] = Field(description="{인과 사전 id: 새 알 확률}. 사전에 없는 id 는 빠진다")


class MasteryOut(BaseModel):
    mastery: dict[str, float] = Field(description="{개념 이름: 알 확률}. 안 풀어 본 개념은 처음 값")


class ReviewItem(BaseModel):
    node_id: int
    concept: str
    p_know: float
    retrievability: float = Field(description="지금 기억하고 있을 확률 (FSRS)")
    reason: Literal["sure_wrong", "due"] = Field(description="sure_wrong = 확실해요라고 했는데 틀렸던 개념")
    due_at: datetime


class ReviewsOut(BaseModel):
    limit: int = Field(description="하루 복습 개념 수 상한")
    done_today: int
    due_total: int = Field(description="복습일이 된 개념 전체 수 (상한에 잘리기 전)")
    items: list[ReviewItem] = Field(description="오늘 복습할 개념. 앞에서부터 푼다")


class CalibrationSummary(BaseModel):
    """2 × 2 표(정답/오답 × 확실/헷갈려요) 하나의 개수와 지표 (learner/calibration.summarize). 분모가 0 이면 null."""
    total: int
    enough: bool = Field(description="답이 20개 이상인가. 아니면 비율을 보여 주기엔 부족")
    sure_right: int
    sure_wrong: int = Field(description="확실해요인데 틀림 (착각)")
    unsure_right: int
    unsure_wrong: int
    sensitivity: float | None = Field(description="맞힌 답 중 확실해요 비율")
    specificity: float | None = Field(description="틀린 답 중 헷갈려요 비율")
    illusion: float | None = Field(description="틀린 답 중 확실해요 비율 (착각률)")
    sure_accuracy: float | None = Field(description="확실해요 답의 정답률")
    unsure_accuracy: float | None = Field(description="헷갈려요 답의 정답률")
    gap: float | None
    gamma: float | None
    bias: float | None = Field(description="확실해요 비율 - 정답률. 양수면 과신")


class CalibrationOut(BaseModel):
    all: CalibrationSummary
    recent: CalibrationSummary = Field(description="최근 recent_days 일")
    earlier: CalibrationSummary = Field(description="그 전")
    recent_days: int
    sure_wrong_concepts: list[str] = Field(description="확실해요라고 했는데 틀렸고 아직 다시 맞히지 못한 개념")


class ReviewQuizIn(BaseModel):
    user_id: UUID
    node_id: int = Field(description="복습할 개념 (GET /learner/reviews 의 node_id)")


class ReviewQuizOut(BaseModel):
    quiz_id: int
    node_id: int
    concept: str
    kind: str = Field(description="용어 뜻 / 헷갈리는 쌍 / 틀린 설명 / O/X")
    content: dict = Field(description="화면용. 보기 고르기는 {question, options}, O/X 는 {statement, options}. "
                                      "헷갈리는 쌍의 options 는 두 개념 이름. 정답 없음")
    guess_p: float = Field(description="찍어서 맞힐 확률 (코드 계산)")


class ReviewAnswerIn(BaseModel):
    user_id: UUID
    quiz_id: int
    answer: int | list[int] = Field(description="고른 보기 번호 (0부터)")
    confidence: Literal[1, 2] | None = Field(default=None, description="1 헷갈려요, 2 확실해요")
    response_ms: int | None = Field(default=None, ge=0)
    answer_changes: int | None = Field(default=None, ge=0)


class ReviewAnswerOut(BaseModel):
    correct: bool
    key: int | list[int] = Field(description="정답 보기 번호")
    explanation: str
    concept: str
    p_know: float = Field(description="반영한 뒤의 알 확률")
    due_at: datetime = Field(description="다음 복습일")


def _conn():
    # psycopg 를 여기서 불러온다. judge_api 를 띄우는 것만으로는 DB 가 필요 없게 (채점 테스트는 DB 없이 돈다)
    from db import get_conn

    return get_conn()


@router.post("/answer", response_model=AnswerOut)
def record_answer(req: AnswerIn) -> AnswerOut:
    guess = guess_for_step(req.kind, req.count)
    with _conn() as conn:
        mastery = state.update_causal(
            conn, str(req.user_id), req.concept_ids, req.correct, guess, confidence=req.confidence,
            response_ms=req.response_ms, answer_changes=req.answer_changes, kind=req.kind)
    return AnswerOut(guess_p=guess, mastery=mastery)


@router.get("/mastery/{user_id}", response_model=MasteryOut)
def read_mastery(user_id: UUID) -> MasteryOut:
    with _conn() as conn:
        return MasteryOut(mastery=state.get_mastery(conn, str(user_id)))


@router.get("/reviews/{user_id}", response_model=ReviewsOut)
def read_reviews(user_id: UUID) -> ReviewsOut:
    with _conn() as conn:
        return ReviewsOut(**state.due_reviews(conn, str(user_id)))


@router.get("/calibration/{user_id}", response_model=CalibrationOut)
def read_calibration(user_id: UUID) -> CalibrationOut:
    with _conn() as conn:
        return CalibrationOut(**state.calibration_report(conn, str(user_id)))


def make_quiz(kind: str, concept: str, desc: str, pair: list[str] | None = None):
    """복습 문제 하나를 만든다 (LLM 호출). pair 는 헷갈리는 쌍일 때 [개념, 이웃]. 테스트는 이 함수를 바꿔 끼운다."""
    from tutor import quiz as qz   # 여기서 불러온다: 학습자 상태만 쓰는 요청은 LLM 모듈이 필요 없게

    return qz.generate(kind, concept, desc, pair)


@router.post("/review/quiz", response_model=ReviewQuizOut)
def review_quiz(req: ReviewQuizIn) -> ReviewQuizOut:
    user = str(req.user_id)
    with _conn() as conn:
        try:
            plan = review.prepare(conn, user, req.node_id)
        except review.NotDue:
            raise HTTPException(status_code=409, detail="오늘 복습할 개념이 아니에요.") from None
    if "pending" in plan:
        return ReviewQuizOut(**plan["pending"])
    # LLM 을 부르는 동안에는 DB 연결을 잡고 있지 않는다
    try:
        quiz = make_quiz(plan["kind"], plan["concept"], plan["desc"], plan.get("pair"))
    except Exception as e:  # 모양 검사 실패(QuizError), 월 한도(BudgetExceeded), API 오류
        log.warning("복습 문제를 만들지 못했어요 (%s, %s): %s", plan["concept"], plan["kind"], e)
        raise HTTPException(status_code=503, detail="문제를 만들지 못했어요. 잠시 뒤에 다시 해 주세요.") from None
    with _conn() as conn:
        return ReviewQuizOut(**review.save(conn, user, req.node_id, quiz))


@router.post("/review/answer", response_model=ReviewAnswerOut)
def review_answer(req: ReviewAnswerIn) -> ReviewAnswerOut:
    with _conn() as conn:
        try:
            return ReviewAnswerOut(**review.answer(
                conn, str(req.user_id), req.quiz_id, req.answer, req.confidence,
                response_ms=req.response_ms, answer_changes=req.answer_changes))
        except review.QuizNotFound:
            raise HTTPException(status_code=404, detail="없는 문제예요.") from None
        except review.AlreadyAnswered:
            raise HTTPException(status_code=409, detail="이미 답한 문제예요.") from None
