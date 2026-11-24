"""1-5 퀴즈 은행 (사람1, #238). 가르치기용·마지막 시험용 퀴즈를 미리 만들어 두고 세 조건이 같이 꺼내 쓴다.

왜: ① 조건마다 퀴즈를 새로 만들면 퀴즈 난이도·오류가 조건마다 달라져 비교가 흐려진다 ② 비용 (세션마다 출제하면 수백 번)
출제는 tutor.quiz.generate 그대로 (모양 검사 + 내용 검사 #234 + 정답 위치 섞기). 카드마다 따로 만든다: 짝 맞추기·헷갈리는 쌍의
짝이 카드의 개념 범위에 따라 달라서 (tutor.agent.make_quiz 와 같은 규칙).
마지막 시험용은 가르치기용과 따로 만들어 겹치지 않는다 (가르칠 때 본 퀴즈를 시험에 다시 내면 외운 것을 잰다).

    python -m eval.bank --per 3      # logs/eval/quiz_bank.json (비용 약 $0.3)
"""
import argparse
import json
import random
from dataclasses import asdict
from pathlib import Path

from generate.llm_client import ROOT
from tutor import agent as ag
from tutor import quiz as qz

BANK_PATH = ROOT / "logs" / "eval" / "quiz_bank.json"
CARDS = (17, 11)
TEST_KINDS = ("용어 뜻", "사례 분류")   # 마지막 시험: 찍어서 맞힐 확률이 낮은 사례 분류 + 뜻을 직접 묻는 용어 뜻
TEST_PER = 2


def build(conn, cards=CARDS, per: int = 3, test_per: int = TEST_PER, log=print) -> dict:
    """{"cards": {카드: {"targets", "scope", "teach": {"개념|종류": [퀴즈]}, "test": {"개념": [퀴즈]}}}}"""
    cmap = ag.ConceptMap.from_db(conn)
    out = {"cards": {}}
    for card in cards:
        targets = ag.card_targets(conn, card)
        scope = cmap.ancestors(targets)
        s = ag.Session("bank", cmap, targets, None, card_id=card)
        teach, test, fails = {}, {}, 0
        for concept in scope:
            for kind in qz.KINDS:
                got = []
                for _ in range(per):
                    try:
                        got.append(asdict(ag.make_quiz(s, concept, kind)))
                    except qz.QuizError as e:
                        fails += 1
                        log(f"   카드 {card} {concept} / {kind}: 출제 실패 {str(e)[:80]}")
                        if "이웃이 없어요" in str(e) or "3개가 안 돼요" in str(e):
                            break   # 이 개념은 이 종류를 낼 수 없다 (몇 번 해도 같다)
                if got:
                    teach[f"{concept}|{kind}"] = got
        for concept in targets:
            test[concept] = []
            for kind in TEST_KINDS:
                for _ in range(test_per):
                    try:
                        test[concept].append(asdict(ag.make_quiz(s, concept, kind)))
                    except qz.QuizError as e:
                        fails += 1
                        log(f"   카드 {card} 시험 {concept} / {kind}: 출제 실패 {str(e)[:80]}")
        out["cards"][str(card)] = {"targets": targets, "scope": scope, "teach": teach, "test": test}
        log(f"카드 {card}: 가르치기용 {sum(len(v) for v in teach.values())}개, 시험용 {sum(len(v) for v in test.values())}개, 실패 {fails}번")
    return out


def save(bank: dict, path: Path = BANK_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def load(path: Path = BANK_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def to_quiz(d: dict) -> qz.Quiz:
    return qz.Quiz(**d)


class Draw:
    """한 세션이 은행에서 퀴즈를 꺼낸다. (개념, 종류)마다 섞은 순서로 돌아가며 (같은 퀴즈가 연달아 나오지 않게)."""

    def __init__(self, card_bank: dict, rng: random.Random):
        self.teach = card_bank["teach"]
        self.rng = rng
        self.order: dict[str, list[int]] = {}
        self.next: dict[str, int] = {}

    def __call__(self, s, concept: str, kind: str) -> qz.Quiz:   # tutor.agent.Session.quiz_maker 모양
        key = f"{concept}|{kind}"
        items = self.teach.get(key)
        if not items:
            raise qz.QuizError(f"{concept} / {kind} 퀴즈가 없어요. 다른 종류를 고르세요")
        if key not in self.order:
            o = list(range(len(items)))
            self.rng.shuffle(o)
            self.order[key], self.next[key] = o, 0
        i = self.order[key][self.next[key] % len(items)]
        self.next[key] += 1
        return to_quiz(items[i])


def main() -> None:
    p = argparse.ArgumentParser(description="1-5 퀴즈 은행 만들기 (비용 발생)")
    p.add_argument("--per", type=int, default=3, help="(개념, 종류)마다 가르치기용 퀴즈 수")
    args = p.parse_args()
    from db import get_conn

    with get_conn() as conn:
        bank = build(conn, per=args.per)
        conn.rollback()
    print(f"저장: {save(bank)}")


if __name__ == "__main__":
    main()
