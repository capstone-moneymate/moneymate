"""튜터 에이전트 시연 (사람1, #201 완료 기준): 지식 상태가 다른 가상 학습자 2명에게 서로 다른 순서를 고르는지 본다.
실제 Opus(튜터)·Haiku(퀴즈 출제)를 부른다 (비용 발생, 한 번에 약 $0.1~0.3).

실행 (worker/ 에서): python -m tutor.demo
결과: 화면 + logs/tutor_demo.json

가상 학습자는 1-5 평가 전 단계의 간단한 규칙이다 (LLM 학습자가 아니다):
- 진짜로 아는 개념 → 정답, 확신해요 / 잘못 아는 개념 → 오답, 확신해요 / 모르는 개념 → 찍기(guess_p 확률로 정답), 애매해요
- explain 으로 설명을 들은 개념은 그 뒤로 안다 (잘못 알던 것도 고쳐진다)
개념 지도는 작은 손 예시다. 실제 카드 개념 지도는 #203 에서 붙인다.
"""
import json
import random
from dataclasses import dataclass, field

from generate.llm_client import ROOT
from tutor import agent as ag
from tutor.mastery import SURE, UNSURE, FakeMastery
from tutor.quiz import Quiz

CMAP = ag.ConceptMap(
    ["순이익", "유통 주식 수", "주당순이익", "주당순자산", "자사주 소각"],
    {
        "순이익": "회사가 한 해 동안 번 돈에서 비용과 세금을 모두 뺀 돈",
        "유통 주식 수": "회사가 발행한 주식 중 회사가 가진 자사주를 빼고 시장에서 거래되는 주식 수",
        "주당순이익": "순이익을 유통 주식 수로 나눈 값. 주식 한 주가 번 돈 (EPS)",
        "주당순자산": "회사의 순자산을 주식 수로 나눈 값. 주식 한 주에 해당하는 자산 (BPS)",
        "자사주 소각": "회사가 가진 자기 주식을 없애는 것. 유통 주식 수가 줄어 주당순이익이 커질 수 있다",
    },
    [("순이익", "주당순이익", 4), ("유통 주식 수", "주당순이익", 4), ("유통 주식 수", "자사주 소각", 4)],
    {"주당순이익": ["주당순자산"]},
)
TARGETS = ["주당순이익", "자사주 소각"]
CARD = "삼성전자, 자사주 3조 원어치 소각 발표"


@dataclass
class Learner:
    name: str
    knows: set[str]
    wrong: set[str] = field(default_factory=set)  # 잘못 알고 있는 개념 (확신하고 틀린다)
    start_p: dict[str, float] = field(default_factory=dict)


LEARNERS = [
    Learner("A 기초는 앎, 자사주 소각을 잘못 앎", {"순이익", "유통 주식 수", "주당순이익"}, {"자사주 소각"},
            {"순이익": 0.97, "유통 주식 수": 0.97, "주당순이익": 0.6}),
    Learner("B 처음 배움", set(), set(), {}),
]


def wrong_answer(q: Quiz):
    if isinstance(q.key, int):
        return (q.key + 1) % len(q.content["options"])
    # 뒤집어도 같은 답([0, 1, 1, 0])이면 정답이 돼 버려서, 그때는 칸마다 0↔1 을 바꾼다 (#204 리뷰).
    # (칩 빈칸은 정답 칩이 서로 달라 뒤집으면 항상 달라지고, 이 경우는 사례 분류에서만 생긴다)
    flipped = list(reversed(q.key))
    return flipped if flipped != q.key else [1 - k for k in q.key]


def respond(learner: Learner, q: Quiz, rng: random.Random):
    c = q.concept
    if c in learner.wrong:
        return wrong_answer(q), SURE
    if c in learner.knows:
        return q.key, SURE
    return (q.key if rng.random() < q.guess_p else wrong_answer(q)), UNSURE


def run(learner: Learner, seed: int = 0) -> ag.Session:
    rng = random.Random(seed)
    s = ag.Session(learner.name, CMAP, TARGETS, FakeMastery({learner.name: dict(learner.start_p)}), card=CARD)
    seen_events = 0
    s = ag.start(s)
    while True:
        for e in s.events[seen_events:]:  # 설명을 들은 개념은 알게 된다
            if e["type"] == "explain":
                learner.knows.add(e["concept"])
                learner.wrong.discard(e["concept"])
        seen_events = len(s.events)
        if s.status != "waiting":
            return s
        _, q = s.pending
        s = ag.answer(s, *respond(learner, q, rng))


def main() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)  # 돈 드는 호출 전에. 새로 받은 저장소에는 logs/ 가 없다
    out = []
    for learner in LEARNERS:
        s = run(learner)
        print(f"\n== {learner.name}: 끝 = {s.finished_by}, 퀴즈 {s.quizzes}개, 모델 호출 {s.calls}번")
        for i, e in enumerate(s.log, 1):
            inp = ", ".join(f"{k}={v}" for k, v in e["input"].items() if k != "text")
            res = e.get("result")
            tail = f"  → {'맞힘' if res['correct'] else '틀림'}·{res['confidence']}" if res else ""
            print(f"   {i}. {e['tool']}({inp}){tail}\n      이유: {e['reason']}")
        out.append({"learner": learner.name, "finished_by": s.finished_by, "log": s.log, "events": s.events,
                    "mastery": s.mastery.get_mastery(learner.name)})
    path = ROOT / "logs" / "tutor_demo.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
