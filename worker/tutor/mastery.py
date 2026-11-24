"""가짜 get_mastery (사람1, #201). 사람2 의 BKT(2-3)가 나오기 전까지 튜터를 개발하려고 둔 대체품이다.
계획 6장 약속 모양 그대로: get_mastery(user_id) -> {concept: p_know}.

갱신 규칙은 일부러 단순하다 (BKT 가 아니다. 숫자에 근거가 없으니 평가·발표에 쓰지 않는다):
- 맞힘 + 확신해요 → 0.97 (앎), 맞힘 + 애매해요 → 0.75 이상, 틀림 → 0.30 이하
진짜 BKT 로 바꿀 때는 get_mastery / update 두 함수의 모양만 맞추면 튜터 코드는 그대로다.
"""
from dataclasses import dataclass, field

SURE, UNSURE = "확신해요", "애매해요"


@dataclass
class FakeMastery:
    p: dict[str, dict[str, float]] = field(default_factory=dict)  # user -> {concept: p_know}

    def get_mastery(self, user_id: str) -> dict[str, float]:
        return dict(self.p.get(user_id, {}))

    def update(self, user_id: str, concept: str, correct: bool, confidence: str, guess_p: float = 0.0) -> float:
        """답 하나를 반영하고 새 알 확률을 돌려준다. guess_p 는 진짜 BKT 가 쓸 자리라 지금은 쓰지 않는다."""
        cur = self.p.setdefault(user_id, {}).get(concept, 0.0)
        if correct and confidence == SURE:
            new = 0.97
        elif correct:
            new = max(cur, 0.75)
        else:
            new = min(cur, 0.30)
        self.p[user_id][concept] = new
        return new
