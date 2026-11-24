"""1-5 가상 학습자 (사람1, #238). 숨긴 정답 지식 상태를 가진 코드 규칙 학습자.

교사(고정 순서·규칙만·에이전트)는 이 상태를 보지 못하고 퀴즈 답만 본다. 평가 지표는 이 숨긴 상태로 잰다
(튜터가 계산한 BKT 가 아니다). 그래서 "기준을 스스로 정했다"는 지적을 피한다.

답하는 규칙 (세 조건에 똑같이 적용):
- 아는 개념: 정답. 단 SLIP(0.1) 확률로 실수해서 틀린다. 확신해요
- 모르는 개념: 찍는다 (보기·칩·바구니를 고르게 무작위로 → 맞힐 확률이 그 퀴즈의 guess_p 와 같다). 애매해요
- 잘못 아는 개념(오개념): 확신하고 틀린다
배우는 규칙:
- 퀴즈 해설을 보거나(답한 뒤) 설명을 들으면, 모르던·잘못 알던 개념을 p_learn 확률로 알게 된다
- 진짜 선수 개념 중 하나라도 모르면 p_learn 에 prereq_effect 를 곱한다 (1.0 상관없음 / 0.5 어려움 / 0.0 못 배움).
  이 값은 결과를 크게 좌우해서 하나로 정하지 않고 셋 다 돌린다. 한계: 진짜 선수 관계도 우리 개념 지도(42개)다
숫자 출발점: p_learn 0.3, 민감도 0.1~0.5 (BKT 배울 확률 문헌값 범위. docs/modules/eval_learner.md), SLIP 은 BKT 실수 0.1 과 같다.
실수는 학생마다 크게 다르다 (Corbett & Anderson 1995, 273·275쪽) → 실험에서 0.05 / 0.2 / 0.3 으로도 돌린다 (BKT 는 0.1 그대로).
확신: 기본은 확신을 내지 않는다 (conf_noise=None → None). 본 비교에 확신 가정을 넣지 않으려고 (고정·규칙은 확신을 안 쓴다).
conf_noise 를 주면 숨긴 상태대로 확신(앎·오개념 = 확신해요, 모름 = 애매해요)을 내되 그 확률로 반대를 낸다 (확신 실험).
"""
import random
from dataclasses import dataclass, field

from tutor.quiz import Quiz

SLIP = 0.1
P_LEARN = 0.3
SURE, UNSURE = "확신해요", "애매해요"


def random_answer(q: Quiz, rng: random.Random):
    """퀴즈 모양 안에서 고르게 무작위로 고른 답 (찍기). 맞힐 확률이 guess_p 와 같다."""
    c = q.content
    if q.kind in ("용어 뜻", "헷갈리는 쌍", "틀린 설명", "O/X"):
        return rng.randrange(len(c["options"]))
    if q.kind == "칩 빈칸":
        return rng.sample(range(len(c["chips"])), len(q.key))
    if q.kind == "짝 맞추기":
        return rng.sample(range(len(c["terms"])), len(c["terms"]))
    if q.kind == "사례 분류":
        return [rng.randrange(len(c["baskets"])) for _ in c["cases"]]
    raise ValueError(q.kind)


def wrong_answer(q: Quiz, rng: random.Random):
    """정답이 아닌 답 하나 (무작위). 오답이 없는 퀴즈는 없다 (모양 검사가 보기 2개 이상을 요구한다)."""
    while True:
        a = random_answer(q, rng)
        if a != q.key:
            return a


@dataclass
class Learner:
    name: str
    known: set[str]
    wrong: set[str] = field(default_factory=set)   # 오개념 (확신하고 틀린다)
    prereq: dict[str, list[str]] = field(default_factory=dict)   # 진짜 선수 관계: 개념 → 먼저 알아야 하는 개념들
    p_learn: float = P_LEARN
    prereq_effect: float = 1.0
    slip: float = SLIP
    conf_noise: float | None = None   # None: 확신을 내지 않음 / 0~1: 그 확률로 확신을 반대로
    rng: random.Random = field(default_factory=random.Random)
    log: list[tuple] = field(default_factory=list)   # (사건, 개념, 결과) 기록

    def knows(self, concept: str) -> bool:
        return concept in self.known

    def respond(self, q: Quiz):
        """(답, 확신). 숨긴 상태대로. 확신은 conf_noise 가 None 이면 None."""
        c = q.concept
        if c in self.wrong:
            ans, conf = wrong_answer(q, self.rng), SURE
        elif c in self.known:
            ans = wrong_answer(q, self.rng) if self.rng.random() < self.slip else q.key
            conf = SURE
        else:
            ans, conf = random_answer(q, self.rng), UNSURE
        if self.conf_noise is None:
            return ans, None
        if self.rng.random() < self.conf_noise:
            conf = UNSURE if conf == SURE else SURE
        return ans, conf

    def learn_chance(self, concept: str) -> float:
        missing = [p for p in self.prereq.get(concept, []) if p not in self.known]
        return self.p_learn * (self.prereq_effect if missing else 1.0)

    def study(self, concept: str, how: str) -> bool:
        """해설(how='feedback')이나 설명(how='explain')을 봤다. 모르던 개념을 배우면 True."""
        if concept in self.known:
            return False
        learned = self.rng.random() < self.learn_chance(concept)
        if learned:
            self.known.add(concept)
            self.wrong.discard(concept)
        self.log.append((how, concept, learned))
        return learned


def profiles(scope: list[str], targets: list[str], edges: list[tuple[str, str, int]]) -> dict[str, dict]:
    """카드 범위(scope)에 맞춘 학습자 4종류의 숨긴 상태. {이름: {"known": set, "wrong": set}}.
    기초 = 범위 안에서 선수 개념이 없는 개념(뿌리)."""
    pre = {c: [a for a, b, _ in edges if b == c and a in scope] for c in scope}
    roots = {c for c in scope if not pre[c]}
    first_target = targets[0]
    return {
        "처음 배움": {"known": set(), "wrong": set()},
        "기초만 앎": {"known": set(roots), "wrong": set()},
        "거의 앎": {"known": set(scope) - set(targets), "wrong": set()},
        "잘못 앎": {"known": set(roots) - {first_target}, "wrong": {first_target}},
    }


def prereq_of(edges: list[tuple[str, str, int]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for a, b, _ in edges:
        out.setdefault(b, []).append(a)
    return out
