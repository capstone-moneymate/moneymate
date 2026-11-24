"""확신 보정 지표 (사람2, 계획 2-5). DB 를 모른다. 개수만 받아 지표를 돌려준다 (개수는 learner/state.py 가 센다).

확신은 [헷갈려요] [확실해요] 두 단계다. 이걸 "확실해요 = 0.9" 같은 확률로 바꾸면 그 숫자를 우리가 정한 셈이 되므로,
확률로 바꾸지 않고 2 × 2 표(정답/오답 × 확실/헷갈려요)에서 바로 계산하는 지표만 쓴다.

                확실해요            헷갈려요
    맞힘     sure_right          unsure_right     (알면서 헷갈려요 = 과소확신)
    틀림     sure_wrong (착각)    unsure_wrong

지표와 출처
  sensitivity  맞힌 답 중 확실해요 비율   sure_right / (sure_right + unsure_right)      "아는 것을 안다고 했나"
  specificity  틀린 답 중 헷갈려요 비율   unsure_wrong / (sure_wrong + unsure_wrong)    "모르는 것을 모른다고 했나"
      Schraw, Kuch & Gutierrez (2013, Learning and Instruction 24): 2 × 2 표로 만드는 지표 10개를 비교했더니
      이 두 개가 가장 잘 설명했다.
  illusion     틀린 답 중 확실해요 비율 (착각률) = 1 - specificity. 가장 위험한 칸
  sure_accuracy / unsure_accuracy  확실해요 답의 정답률, 헷갈려요 답의 정답률. 차이(gap)가 클수록 잘 구분한 것
  gamma        (a·d - b·c) / (a·d + b·c).  +1 이면 확신이 정답을 완전히 가르고, 0 이면 무관
      Nelson (1984, Psychological Bulletin 95): 확신과 정답이 얼마나 같이 움직이는지 보는 지표로 gamma 를 권했다.
  bias         확실해요 비율 - 정답률 = (sure_wrong - unsure_right) / 전체.  양수면 과신, 음수면 과소확신
      Schraw (2009, Metacognition and Learning 4) 의 bias 지수를 두 단계 확신(확실 1, 헷갈려요 0)에 적용한 것.

손계산 (답 20개: 확실+맞힘 9, 확실+틀림 3, 헷갈려요+맞힘 3, 헷갈려요+틀림 5)
  sensitivity 9/12 = 0.75, specificity 5/8 = 0.625, illusion 3/8 = 0.375
  sure_accuracy 9/12 = 0.75, unsure_accuracy 3/8 = 0.375, gap 0.375
  gamma (9·5 - 3·3) / (9·5 + 3·3) = 36/54 = 0.667,  bias (3 - 3)/20 = 0

brier 는 확률 예측(예: BKT 알 확률로 만든 "맞힐 확률")을 실제 결과와 비교할 때 쓴다 (Brier 1950). 확신 버튼에는 쓰지 않는다.
"""
from dataclasses import dataclass

MIN_ANSWERS = 20  # 이보다 적으면 비율이 한두 문제에 크게 흔들려서 "아직 부족"으로 알린다 (계획: 20~30개)


@dataclass(frozen=True)
class Table:
    """정답/오답 × 확실/헷갈려요 개수."""
    sure_right: int = 0
    sure_wrong: int = 0
    unsure_right: int = 0
    unsure_wrong: int = 0

    def __post_init__(self):
        if min(self.sure_right, self.sure_wrong, self.unsure_right, self.unsure_wrong) < 0:
            raise ValueError("개수는 0 이상이어야 해요")

    @property
    def total(self) -> int:
        return self.sure_right + self.sure_wrong + self.unsure_right + self.unsure_wrong


def _ratio(a: int, b: int) -> float | None:
    """a / b. 분모가 0 이면 계산할 수 없으니 None."""
    return a / b if b else None


def summarize(t: Table) -> dict:
    """2 × 2 표 하나의 지표. 분모가 0 인 지표는 None (예: 틀린 답이 없으면 specificity 를 알 수 없다)."""
    a, b, c, d = t.sure_right, t.sure_wrong, t.unsure_right, t.unsure_wrong
    sure_acc, unsure_acc = _ratio(a, a + b), _ratio(c, c + d)
    specificity = _ratio(d, b + d)
    return {
        "total": t.total,
        "enough": t.total >= MIN_ANSWERS,
        "sure_right": a, "sure_wrong": b, "unsure_right": c, "unsure_wrong": d,
        "sensitivity": _ratio(a, a + c),
        "specificity": specificity,
        "illusion": None if specificity is None else 1 - specificity,
        "sure_accuracy": sure_acc,
        "unsure_accuracy": unsure_acc,
        "gap": None if sure_acc is None or unsure_acc is None else sure_acc - unsure_acc,
        "gamma": _ratio(a * d - b * c, a * d + b * c),
        "bias": _ratio(b - c, t.total),
    }


def brier(probs: list[float], outcomes: list[bool]) -> float | None:
    """확률 예측의 Brier 점수: (예측 확률 - 결과)² 의 평균. 0 이 완벽, 늘 0.5 라고 하면 0.25. 비어 있으면 None."""
    if len(probs) != len(outcomes):
        raise ValueError("예측과 결과의 개수가 달라요")
    if not probs:
        return None
    for p in probs:
        if not 0 <= p <= 1:
            raise ValueError(f"확률은 0~1 이어야 해요: {p}")
    return sum((p - (1.0 if o else 0.0)) ** 2 for p, o in zip(probs, outcomes)) / len(probs)
