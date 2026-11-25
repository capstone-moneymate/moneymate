"""BKT 알 확률 갱신 (사람2, 계획 2-3). Corbett & Anderson (1995) 지식 추적의 식 그대로다.
DB 를 모른다. 숫자만 받아 숫자를 돌려준다 (저장은 learner/state.py).

답 하나가 들어오면 두 단계로 고친다.
  1. 베이즈 갱신: "맞힌 사람 중 실제로 아는 사람 비율" (찍어서 맞힘·실수로 틀림을 고려)
       맞힘  p' = p(1-실수) / (p(1-실수) + (1-p)추측)
       틀림  p' = p·실수 / (p·실수 + (1-p)(1-추측))
  2. 배움 반영: 푸는 동안 배웠을 수 있으니 모르는 쪽의 일부를 더한다   p'' = p' + (1-p')배움

손계산 (처음 0.25, 4지선다 추측 0.25, 실수 0.1, 배움 0.2):
  맞힘  0.225 / (0.225 + 0.1875) = 0.545 → 0.545 + 0.455 × 0.2 = 0.636
  틀림  0.025 / (0.025 + 0.5625) = 0.043 → 0.043 + 0.957 × 0.2 = 0.234

파라미터의 출처
  추측  문제 형식에서 코드가 계산해 넘긴다 (4지선다 0.25, O/X 0.5, 칩 빈칸 약 0.08. worker/tutor/quiz.py 의 guess_p)
  실수·처음·배움  아래 기본값. 1997 Cognitive Geometry Tutor 가 실제로 쓰던 출발값 세트(처음 0.25, 배움 0.2, 실수 0.1.
                 Cen, Koedinger & Junker 2007, 표 1)를 그대로 따랐다 (2026-11-25, 그 전에는 처음 0.3·배움 0.1).
                 우리 데이터로 학습한 값이 아니라서 민감도 분석으로 결론이 흔들리지 않는지 본다 (corrects_to_know).
                 데이터가 쌓이면 pyBKT 로 학습해 바꾼다. 근거와 한계는 docs/modules/learner_bkt.md
"""
from dataclasses import dataclass

GUESS_MIN = 0.01  # 추측이 0 이면 한 번 맞힌 순간 알 확률이 1 이 되고 그 뒤로는 틀려도 내려오지 않는다. 그걸 막는 계산용 하한
GUESS_MAX = 0.5   # 보기가 2개인 문제(O/X)가 가장 찍기 쉽다. 이보다 크면 넘긴 값이 잘못된 것


@dataclass(frozen=True)
class Params:
    p_init: float = 0.25  # 처음 보는 개념의 알 확률
    p_learn: float = 0.2  # 한 문제를 푸는 동안 배울 확률. 계속 틀려도 알 확률은 이 값 아래로 내려가지 않는다
    p_slip: float = 0.1   # 알아도 실수로 틀릴 확률 (계획: 0.1 이하)

    def __post_init__(self):
        for name in ("p_init", "p_learn", "p_slip"):
            v = getattr(self, name)
            if not 0 <= v < 1:
                raise ValueError(f"{name} 는 0 이상 1 미만이어야 해요: {v}")


DEFAULT = Params()


def clamp_guess(guess: float) -> float:
    """문제 형식에서 계산한 추측 확률을 계산에 쓸 범위로 맞춘다."""
    return min(max(float(guess), GUESS_MIN), GUESS_MAX)


def posterior(p: float, correct: bool, guess: float, slip: float = DEFAULT.p_slip) -> float:
    """1단계 베이즈 갱신만. 답을 보고 고친 "원래 알고 있었을 확률"."""
    if not 0 <= p <= 1:
        raise ValueError(f"알 확률은 0~1 이어야 해요: {p}")
    g = clamp_guess(guess)
    if correct:
        know, not_know = p * (1 - slip), (1 - p) * g
    else:
        know, not_know = p * slip, (1 - p) * (1 - g)
    total = know + not_know
    return p if total == 0 else know / total


def update(p: float, correct: bool, guess: float, params: Params = DEFAULT) -> float:
    """답 하나를 반영한 새 알 확률 (베이즈 갱신 → 배움 반영)."""
    post = posterior(p, correct, guess, params.p_slip)
    return post + (1 - post) * params.p_learn


def corrects_to_know(guess: float, params: Params = DEFAULT, know_p: float = 0.95, limit: int = 50) -> int | None:
    """처음 보는 개념을 몇 번 연달아 맞혀야 "안다"(know_p 이상)가 되는가. 민감도 분석용.
    limit 번 안에 못 넘으면 None."""
    p = params.p_init
    for n in range(1, limit + 1):
        p = update(p, True, guess, params)
        if p >= know_p:
            return n
    return None
