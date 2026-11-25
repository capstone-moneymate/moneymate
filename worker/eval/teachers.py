"""1-5 교사 세 가지 (사람1, #238). 같은 가상 학습자·같은 퀴즈 은행·같은 BKT 로 가르친다.

① fixed  고정 순서: 개념 지도 순서(선수 관계를 보지 않는다)대로 돌아가며 용어 뜻. BKT 를 보지 않는다
② rules  규칙만: 배울 준비가 된(#199 ready) 개념 중 BKT 알 확률이 가장 낮은 것. 종류는 알 확률로 정한다
          (0.5 미만 용어 뜻 / 0.8 미만 사례 분류 / 그 이상 칩 빈칸). 목표 개념이 모두 0.95 를 넘으면 끝
③ agent  튜터 에이전트(tutor.agent, Opus). 제거 실험: no_bkt(알 확률을 늘 처음 값으로 보여 줌), no_prereq(선수 관계 없는 지도).
          확신은 본 비교에서 넘기지 않고(가정 없이 같은 정보로), 따로 잡음 0 / 0.4 로 넣어 효과를 본다 (eval.run 의 conf 설정)
공정하게: 세 조건 모두 퀴즈 상한이 같고, 답한 뒤 해설을 보여 준다(학습자가 배울 기회). 틀리면 고정·규칙도 설명을 한 번 보여 준다
(에이전트는 설명을 스스로 고른다). 학습자가 퀴즈를 맞혔는지·알게 됐는지는 숨긴 상태로 기록한다.
"""
import random
from dataclasses import dataclass, field

from concepts.prereq_check import KNOW_P, ready_concepts
from eval.learner import Learner
from learner import bkt
from tutor import agent as ag
from tutor import quiz as qz


class MemMastery:
    """메모리 BKT. 사람2 learner.bkt 와 같은 식. 값은 params (기본 bkt.DEFAULT = 지금 앱의 값). 사람2 가 값을 바꾸기 전에도
    실험에서 다른 값으로 돌려 볼 수 있게 받는다 (eval.run --bkt). blind=True 면 제거 실험 no_bkt:
    갱신은 하지만 늘 처음 값을 보여 준다 (에이전트가 진도를 못 본다)."""

    def __init__(self, concepts, blind: bool = False, params: bkt.Params = bkt.DEFAULT):
        self.params = params
        self.p = {c: params.p_init for c in concepts}
        self.blind = blind

    def get_mastery(self, user_id=None) -> dict[str, float]:
        return {c: self.params.p_init for c in self.p} if self.blind else dict(self.p)

    def answer(self, user_id, quiz, response, correct, confidence, **kw) -> float:
        self.p[quiz.concept] = bkt.update(self.p.get(quiz.concept, self.params.p_init), correct, quiz.guess_p, self.params)
        return self.params.p_init if self.blind else self.p[quiz.concept]


@dataclass
class Episode:
    """세션 하나의 기록. mastered_at: 숨긴 상태로 목표 개념을 모두 알게 된 순간까지 낸 퀴즈 수 (끝까지 못 가면 None)."""
    targets: list[str]
    quizzes: int = 0
    explains: int = 0
    mastered_at: int | None = None
    history: list[dict] = field(default_factory=list)
    finished_by: str = ""

    def check(self, learner: Learner):
        if self.mastered_at is None and all(learner.knows(t) for t in self.targets):
            self.mastered_at = self.quizzes


def _ask(q: qz.Quiz, learner: Learner, mastery, ep: Episode, conf_on: bool = True):
    """퀴즈 하나: 학습자가 답하고 → BKT 갱신 → 해설을 보고 배울 기회. (정답 여부, 확신) 을 돌려준다."""
    knew = learner.knows(q.concept)
    ans, conf = learner.respond(q)
    correct = qz.grade(q, ans)
    ep.quizzes += 1
    mastery.answer("sim", q, ans, correct, conf if conf_on else None)
    learned = learner.study(q.concept, "feedback")
    ep.history.append({"concept": q.concept, "kind": q.kind, "correct": correct, "knew": knew, "learned": learned})
    ep.check(learner)
    return correct, conf


def _explain(concept: str, learner: Learner, ep: Episode):
    learner.study(concept, "explain")
    ep.explains += 1
    ep.check(learner)


def fixed(scope, targets, learner: Learner, draw, mastery, cap: int) -> Episode:
    ep = Episode(targets)
    ep.check(learner)
    i = misses = 0
    while ep.quizzes < cap:
        c = scope[i % len(scope)]
        i += 1
        try:
            q = draw(None, c, "용어 뜻")
        except qz.QuizError:
            misses += 1
            if misses >= len(scope):   # 한 바퀴 내내 없다: 은행에 용어 뜻 퀴즈가 없음 (그대로 두면 끝나지 않는다, #239 리뷰)
                raise qz.QuizError("퀴즈 은행에 이 범위의 용어 뜻 퀴즈가 없어요") from None
            continue
        misses = 0
        correct, _ = _ask(q, learner, mastery, ep)
        if not correct:
            _explain(c, learner, ep)
    ep.finished_by = "quiz_limit"
    return ep


RULE_KINDS = (("용어 뜻", 0.5), ("사례 분류", 0.8), ("칩 빈칸", 1.01))
FALLBACK = ("용어 뜻", "사례 분류", "틀린 설명", "O/X")


def rule_kind(p: float) -> str:
    return next(k for k, upper in RULE_KINDS if p < upper)


def rules(scope, targets, edges, learner: Learner, draw, mastery, cap: int) -> Episode:
    ep = Episode(targets)
    ep.check(learner)
    while ep.quizzes < cap:
        m = mastery.get_mastery()
        if all(m[t] >= KNOW_P for t in targets):
            ep.finished_by = "all_known"
            return ep
        ready = [c for c in ready_concepts("sim", scope, edges, m) if m[c] < KNOW_P]
        if not ready:   # 순환을 끊은 지도라 뿌리는 늘 준비됨. 그래도 없으면 범위에서 가장 낮은 것
            ready = [c for c in scope if m[c] < KNOW_P]
        c = min(ready, key=lambda x: (m[x], scope.index(x)))
        q = None
        for kind in (rule_kind(m[c]), *FALLBACK):
            try:
                q = draw(None, c, kind)
                break
            except qz.QuizError:
                continue
        if q is None:
            break
        correct, _ = _ask(q, learner, mastery, ep)
        if not correct:
            _explain(c, learner, ep)
    ep.finished_by = ep.finished_by or "quiz_limit"
    return ep


def agent(cmap: ag.ConceptMap, targets, learner: Learner, draw, mastery, cap: int, title: str = "",
          ) -> tuple[Episode, ag.Session]:
    """튜터 에이전트로 가르친다 (Opus 호출, 비용 발생). 설명 사건이 오면 학습자가 배울 기회를 얻는다.
    확신은 학습자가 낸 것을 그대로 넘긴다 (Learner.conf_noise 가 None 이면 None)."""
    ep = Episode(targets)
    ep.check(learner)
    s = ag.Session("sim", cmap, targets, mastery, card=title, max_quizzes=cap, quiz_maker=draw)
    seen = 0
    s = ag.start(s)
    while True:
        for e in s.events[seen:]:
            if e["type"] == "explain":
                _explain(e["concept"], learner, ep)
        seen = len(s.events)
        if s.status != "waiting":
            ep.finished_by = s.finished_by or s.status
            return ep, s
        _, q = s.pending
        knew = learner.knows(q.concept)
        ans, conf = learner.respond(q)
        ep.quizzes += 1
        learned = learner.study(q.concept, "feedback")   # 답한 뒤 해설 (화면의 graded 이벤트)
        ep.history.append({"concept": q.concept, "kind": q.kind, "correct": qz.grade(q, ans), "knew": knew,
                           "learned": learned})
        ep.check(learner)
        s = ag.answer(s, ans, conf)   # 확신은 학습자가 낸 그대로 (기본 None: 본 비교는 확신 없이)


PRIOR_KIND, PRIOR_PER = "용어 뜻", 2


def prior_record(card_bank: dict, scope, learner: Learner, mastery, rng: random.Random, per: int = PRIOR_PER) -> list[dict]:
    """과거 기록: 세션 전에 학습자가 범위의 개념마다 은행의 용어 뜻 퀴즈 앞 per 개를 혼자 푼다 (교사 없음).
    실제 서비스에서는 BKT 가 카드를 넘어 쌓여서, 기초를 아는 학습자는 앞선 카드에서 이미 맞힌 기록이 있다. 기록이 없으면
    아는 선수 개념도 처음 값(p_init)에서 시작해 퀴즈 6개를 확인에만 쓴다 (2026-11-24 기록 없이 돌린 규칙 조건에서 확인).
    답은 세션과 같은 respond / grade 로 숨긴 상태대로 (아는 개념도 실수, 모르는 개념은 찍기). 배우지 않는다 (지난 일).
    교사에게 숨긴 상태가 아니라 잡음 섞인 답 기록만 BKT 로 넘긴다. 세션 퀴즈 수에 세지 않는다. 씨앗이 따로라 세 조건이 같다."""
    saved, learner.rng = learner.rng, rng
    out = []
    try:
        for c in scope:
            for d in card_bank["teach"].get(f"{c}|{PRIOR_KIND}", [])[:per]:
                q = qz.Quiz(**d)
                ans, _ = learner.respond(q)
                correct = qz.grade(q, ans)
                mastery.answer("sim", q, ans, correct, None)
                out.append({"concept": c, "correct": correct})
    finally:
        learner.rng = saved
    return out


def final_test(test_bank: dict, targets, learner: Learner, rng: random.Random) -> tuple[int, int]:
    """마지막 고정 시험: 목표 개념마다 시험용 퀴즈 (가르칠 때 안 쓴 것). 배우지 않고 답만. (맞힘, 문제 수)."""
    saved, learner.rng = learner.rng, rng
    right = total = 0
    try:
        for t in targets:
            for d in test_bank.get(t, []):
                q = qz.Quiz(**d)
                ans, _ = learner.respond(q)
                right += qz.grade(q, ans)
                total += 1
    finally:
        learner.rng = saved
    return right, total
