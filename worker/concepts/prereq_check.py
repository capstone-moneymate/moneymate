"""개념 지도 선수 관계 순환 검사와 ready (사람1, #199). 규칙은 concepts/prereq.dl, 엔진은 concepts/datalog.py.
코드는 사실을 넣고 결론을 읽기만 한다. 무엇이 순환이고 무엇이 준비됐는지는 규칙이 정한다.

순환 끊기: 규칙이 "순환 위에 있는 연결"(cycle_edge)을 내면, 그중 표(votes)가 가장 적은 연결 하나를 빼고 다시 계산한다.
순환이 없어질 때까지 반복한다. 표가 같으면 (앞, 뒤) 이름 순으로 먼저인 것을 뺀다 (돌릴 때마다 결과가 같게).
표가 적다 = 다수결에서 덜 확실했던 연결이라 먼저 의심한다 (#198 ④).

ready: BKT 알 확률(get_mastery, 사람2 2-3)이 KNOW_P 이상이면 "안다"로 넣는다. 0.95 는 Corbett & Anderson (1995)
지식 추적에서 숙달로 보는 기준이다.
"""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from concepts import datalog

RULES = Path(__file__).with_name("prereq.dl")
KNOW_P = 0.95


@lru_cache(maxsize=1)
def _rules() -> datalog.Program:
    return datalog.parse(RULES.read_text(encoding="utf-8"))


@dataclass
class Checked:
    kept: list[tuple[str, str, int]]     # 순환이 없는 선수 관계 (앞, 뒤, 표)
    removed: list[tuple[str, str, int]]  # 순환을 끊으려고 뺀 연결 (뺀 순서대로)


def cycle_edges(edges: list[tuple[str, str, int]]) -> set[tuple[str, str]]:
    """순환 위에 있는 연결 (앞, 뒤). 비어 있으면 순환이 없다."""
    facts = {"prereq": {(a, b) for a, b, _ in edges}}
    return datalog.evaluate(_rules(), facts).get("cycle_edge")


def break_cycles(edges: list[tuple[str, str, int]]) -> Checked:
    """순환이 없어질 때까지 순환 위 연결 중 표가 가장 적은 것을 하나씩 뺀다."""
    kept, removed = list(edges), []
    while True:
        on_cycle = cycle_edges(kept)
        if not on_cycle:
            return Checked(kept, removed)
        drop = min((e for e in kept if (e[0], e[1]) in on_cycle), key=lambda e: (e[2], e[0], e[1]))
        kept.remove(drop)
        removed.append(drop)


def ready_concepts(user: str, concepts: list[str], edges: list[tuple[str, str, int]],
                   mastery: dict[str, float], know_p: float = KNOW_P) -> list[str]:
    """user 가 지금 배울 준비가 된 개념 (concepts 순서). edges 는 순환을 끊은 뒤의 선수 관계여야 한다.
    mastery: {개념: 알 확률}. 없는 개념은 모르는 것으로 본다."""
    facts = {
        "prereq": {(a, b) for a, b, _ in edges},
        "concept": {(c,) for c in concepts},
        "user": {(user,)},
        "knows": {(user, c) for c, p in mastery.items() if p >= know_p},
    }
    ready = {c for u, c in datalog.evaluate(_rules(), facts).get("ready") if u == user}
    return [c for c in concepts if c in ready]
