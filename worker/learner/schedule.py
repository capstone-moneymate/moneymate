"""FSRS 복습 일정 계산 (사람2, 계획 2-4). DB 를 모른다 (저장은 learner/state.py).

일정 계산은 공식 구현 py-fsrs(open-spaced-repetition, Anki 에 내장된 스케줄러와 같은 FSRS-6)를 그대로 쓴다.
가중치 21개는 패키지의 공개 기본값이다 (실제 복습 기록으로 학습된 값). 우리가 정한 숫자가 아니다.

우리가 바꾼 것 3가지
  1. 평가 버튼을 사용자가 누르지 않는다. 정답·확신·응답 시간·답 변경으로 코드가 평가를 정한다 (rate)
  2. 복습 단위가 카드 한 장이 아니라 개념이다. 같은 개념을 매번 다른 문제로 묻는다 (기억 상태는 개념마다 하나)
  3. 같은 날 다시 보는 단계(learning steps, Anki 의 1분·10분)를 뺐다. 하루 한 번 들어오는 앱이라 간격을 날 단위로만 둔다

자동 평가 (rate). FSRS 의 평가 4단계에 이렇게 맞춘다.
  틀림                              → Again (다시)
  맞힘 + 헷갈려요                    → Hard  (어려움)
  맞힘 + 확실해요 (또는 확신 없음)     → Good  (알맞음)
  맞힘 + 확실해요 + 빨랐고 답을 안 바꿈 → Easy  (쉬움)
정답이 주 신호다. 확신은 사용자가 직접 누른 값이라 그다음이고, 응답 시간과 답 변경은 Good 을 Easy 로 올릴 때만 쓴다.
평가의 뜻은 Anki 매뉴얼의 정의를 옮긴 것이다: Hard = 맞혔지만 의심이 있었거나 오래 걸림, Easy = 맞혔고 힘이 들지 않음.
Easy 는 다음 복습을 가장 멀리 미루는 평가라서, 모든 신호가 같은 쪽을 가리킬 때만 준다.

손계산 (처음 보는 개념, 기본 가중치): 처음 안정도는 평가별 가중치 그대로다.
  Again 0.212일, Hard 1.2931일, Good 2.3065일, Easy 8.2956일
  안정도 = 기억 확률이 90% 로 떨어질 때까지 걸리는 날 수. 다음 복습은 그 날 수를 반올림 (최소 1일)
  → Again·Hard 1일 뒤, Good 2일 뒤, Easy 8일 뒤
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler, State

RETENTION = 0.9       # 기억 확률이 이 값으로 떨어질 때 복습 (FSRS 기본값)
DAILY_LIMIT = 5       # 하루 복습 개념 수 상한 (계획: 예 5개)
FAST_QUANTILE = 0.25  # "빨랐다" = 내가 같은 형식 문제를 맞혔던 시간 중 빠른 쪽 1/4 안. 문헌 값이 아니라 우리가 정한 기준
MIN_TIMES = 8         # 비교할 기록이 이보다 적으면 시간은 보지 않는다

SCHEDULER = Scheduler(desired_retention=RETENTION, learning_steps=(), relearning_steps=(), enable_fuzzing=False)

SURE, UNSURE = 2, 1
_CONFIDENCE_WORDS = {"확실해요": SURE, "확신해요": SURE, "헷갈려요": UNSURE, "애매해요": UNSURE}


@dataclass(frozen=True)
class Memory:
    """개념 하나의 기억 상태 (user_concept_state 의 FSRS 칸)."""
    stability: float       # 안정도 (일)
    difficulty: float      # 난이도 (1~10)
    last_review: datetime
    due: datetime          # 다음 복습 시각


def normalize_confidence(value) -> int | None:
    """확신을 1(헷갈려요) / 2(확실해요) / None 으로. 화면 글자(예전 글자 포함)로 와도 받는다."""
    if value is None:
        return None
    if value in (SURE, UNSURE):
        return int(value)
    if isinstance(value, str) and value in _CONFIDENCE_WORDS:
        return _CONFIDENCE_WORDS[value]
    raise ValueError(f"확신 값은 1, 2 또는 화면 글자여야 해요: {value!r}")


def is_fast(response_ms: int | None, past_ms: list[int]) -> bool:
    """이번 응답이 내 평소보다 빨랐나. past_ms 는 같은 형식 문제를 맞혔던 지난 응답 시간들.
    사람마다 문제 형식마다 속도가 달라서, 고정된 초가 아니라 내 기록 안에서의 위치로 본다."""
    if response_ms is None or len(past_ms) < MIN_TIMES:
        return False
    ordered = sorted(past_ms)
    cut = ordered[max(0, int(len(ordered) * FAST_QUANTILE) - 1)]  # 빠른 쪽 1/4 의 마지막 값
    return response_ms <= cut


def rate(correct: bool, confidence=None, fast: bool = False, answer_changes: int | None = None) -> Rating:
    """답 하나를 FSRS 평가로 바꾼다 (사용자가 평가 버튼을 누르는 자리를 대신한다)."""
    if not correct:
        return Rating.Again
    c = normalize_confidence(confidence)
    if c == UNSURE:
        return Rating.Hard
    if c == SURE and fast and not answer_changes:
        return Rating.Easy
    return Rating.Good


def review(memory: Memory | None, rating: Rating, now: datetime) -> Memory:
    """평가 하나를 반영한 새 기억 상태. memory 가 None 이면 처음 보는 개념."""
    card = Card(card_id=0) if memory is None else Card(
        card_id=0, state=State.Review, stability=memory.stability, difficulty=memory.difficulty,
        due=memory.due, last_review=memory.last_review)
    card, _ = SCHEDULER.review_card(card, rating, _utc(now))
    return Memory(card.stability, card.difficulty, card.last_review, card.due)


def retrievability(memory: Memory, now: datetime) -> float:
    """지금 이 개념을 기억하고 있을 확률 (0~1). 안정도만큼 날이 지나면 0.9. 지난 시간은 날 단위로 센다 (패키지 동작)."""
    card = Card(card_id=0, state=State.Review, stability=memory.stability, difficulty=memory.difficulty,
                due=memory.due, last_review=memory.last_review)
    return SCHEDULER.get_card_retrievability(card, _utc(now))


def _utc(t: datetime) -> datetime:
    if t.tzinfo is None:
        raise ValueError("시각에는 시간대가 있어야 해요")
    return t.astimezone(timezone.utc)
