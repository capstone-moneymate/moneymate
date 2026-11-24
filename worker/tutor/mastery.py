"""튜터의 지식 상태 (사람1, #201 → #230). 튜터는 두 함수만 쓴다:
    get_mastery(user_id) -> {개념 이름: 알 확률}
    answer(user_id, quiz, response, correct, confidence, response_ms=, answer_changes=) -> 새 알 확률

DbMastery (실제): 사람2의 BKT(learner/state.py)로 알 확률을 고치고, 튜터 답을 concept_answers 에 남긴다.
    source='tutor', card_id, attempt_no. 사람2의 확신 점검과 고스트("개념 단계 N문제 필요")가 이 기록을 읽는다.
    시도 번호: 개념 단계는 카드의 첫 답 단계보다 먼저 푼다. 다시 풀 때 그 시점의 user_answers 최대 번호는 아직 지난
    시도라서, 개념 단계 답은 "그 사용자·카드의 최대 번호 + 1"(기록 없으면 1)을 써야 이어서 풀 본 문제와 같은 시도로 묶인다
    (사람2와 맞춘 규칙, #216). 세션에서 처음 답할 때 한 번 정하고 그 세션의 답은 모두 같은 번호다.
    커밋: 답 하나마다 알 확률 갱신과 답 기록을 함께 커밋한다 (state.py 는 커밋하지 않고 부르는 쪽이 한다).
    LLM 이 다음 도구를 고르기 전에 커밋해서, 그 호출이 실패해도 학습자의 답은 남는다.

FakeMastery (DB 없는 테스트용): 갱신 규칙이 일부러 단순하다 (BKT 가 아니다. 숫자에 근거가 없으니 평가·발표에 쓰지 않는다).
    맞힘 + 확신해요 → 0.97 (앎), 맞힘 + 애매해요 → 0.75 이상, 틀림 → 0.30 이하
"""
import json
from dataclasses import dataclass, field
from typing import Protocol

from learner import state
from learner.schedule import normalize_confidence

SURE, UNSURE = "확신해요", "애매해요"   # learner.schedule.normalize_confidence 가 받는 글자 (2 / 1)


class Mastery(Protocol):
    def get_mastery(self, user_id: str) -> dict[str, float]: ...

    def answer(self, user_id: str, quiz, response, correct: bool, confidence, *,
               response_ms: int | None = None, answer_changes: int | None = None) -> float: ...


@dataclass
class FakeMastery:
    p: dict[str, dict[str, float]] = field(default_factory=dict)  # user -> {concept: p_know}

    def get_mastery(self, user_id: str) -> dict[str, float]:
        return dict(self.p.get(user_id, {}))

    def update(self, user_id: str, concept: str, correct: bool, confidence: str, guess_p: float = 0.0) -> float:
        """답 하나를 반영하고 새 알 확률을 돌려준다. guess_p 는 쓰지 않는다 (진짜 BKT 만 쓴다)."""
        cur = self.p.setdefault(user_id, {}).get(concept, 0.0)
        if correct and confidence == SURE:
            new = 0.97
        elif correct:
            new = max(cur, 0.75)
        else:
            new = min(cur, 0.30)
        self.p[user_id][concept] = new
        return new

    def answer(self, user_id, quiz, response, correct, confidence, *, response_ms=None, answer_changes=None) -> float:
        return self.update(user_id, quiz.concept, correct, confidence, quiz.guess_p)


class DbMastery:
    """사람2의 BKT + concept_answers 기록. conn 은 psycopg 연결. commit=False 는 테스트(끝에 rollback)용."""

    SOURCE = "tutor"

    def __init__(self, conn, card_id: int | None = None, *, commit: bool = True):
        self.conn, self.card_id, self.commit = conn, card_id, commit
        self._attempt: dict[str, int | None] = {}

    def get_mastery(self, user_id: str) -> dict[str, float]:
        return state.get_mastery(self.conn, user_id)

    def attempt_no(self, user_id: str) -> int | None:
        """이 세션의 시도 번호. 카드가 없으면(카드 밖에서 부른 튜터) 비운다."""
        if user_id not in self._attempt:
            if self.card_id is None:
                self._attempt[user_id] = None
            else:
                (last,) = self.conn.execute(
                    "SELECT COALESCE(MAX(attempt_no), 0) FROM user_answers WHERE user_id = %s::uuid AND card_id = %s",
                    (user_id, self.card_id)).fetchone()
                self._attempt[user_id] = last + 1
        return self._attempt[user_id]

    def answer(self, user_id, quiz, response, correct, confidence, *, response_ms=None, answer_changes=None) -> float:
        attempt = self.attempt_no(user_id)
        p = state.update(self.conn, user_id, quiz.concept, correct, quiz.guess_p, confidence,
                         response_ms=response_ms, answer_changes=answer_changes, kind=quiz.kind)
        (node_id,) = self.conn.execute("SELECT id FROM concept_nodes WHERE label = %s", (quiz.concept,)).fetchone()
        self.conn.execute(
            """INSERT INTO concept_answers (user_id, node_id, source, card_id, attempt_no, quiz_kind, guess_p, quiz,
                                            answer, is_correct, confidence, response_ms, answer_changes)
               VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)""",
            (user_id, node_id, self.SOURCE, self.card_id, attempt, quiz.kind, quiz.guess_p,
             json.dumps(quiz.content, ensure_ascii=False), json.dumps(response, ensure_ascii=False), correct,
             normalize_confidence(confidence), response_ms, answer_changes),
        )
        if self.commit:
            self.conn.commit()
        return p

