"""판단 근거 규칙 채점 (A). 키워드·연결어로 루브릭 9점(증거 0~2·추론 0~4·반박 0~3)을 매긴다.

Claude 채점(judge.py, 4주차)이 실패할 때 쓰는 대체 수단이고, 증거 점수는 Claude 채점 때도 이 코드가 매긴다.
규칙은 일부러 보수적이다: 키워드가 없으면 점수를 주지 않는다.

사용 예:
    from generate.rule_judge import grade
    r = grade(answer_text, key_facts=card["key_facts"], chain=[{"name": "기준금리 동결", "aliases": ["동결"]}, ...])
    r.rubric  # {"evidence": 2, "reasoning": 3, "rebuttal": 1}
    r.score   # 67  (100점 환산, 반올림)

입력 형식 (초안, C와 맞출 것)
- key_facts: cards.key_facts. [{"text": "한은 기준금리 3.00% 동결", "keywords": ["동결", "3.00%", "3%"]}, ...]
  keywords 중 하나라도 답안에 있으면 그 사실을 쓴 것으로 본다
- chain: 그 카드의 인과 경로 개념 순서. [{"name": ..., "aliases": [...]}, ...] (concepts 테이블 행)

점수 기준
- 증거: 0 = 핵심 사실 없음 / 1 = 사실 1개, 또는 2개 이상이지만 연결어 없음 / 2 = 사실 2개 이상 + 판단과 잇는 연결어
- 추론(SOLO): 0 = 경로 개념 없음 / 1 = 개념 1개 / 2 = 개념 2개 이상, 연결어 없음 /
  3 = 개념 2개 이상 + 연결어 / 4 = 개념 3개 이상 + 연결어 2개 이상
- 반박: 0 = 없음 / 1 = 반대·한계를 말하는 표현만 / 2 = 그 문장에 다른 힘(개념·사실)을 함께 씀 /
  3 = 2 + 조건(만약·~라면·~경우)으로 언제 달라지는지 씀
"""
import re
from dataclasses import dataclass

MAX = {"evidence": 2, "reasoning": 4, "rebuttal": 3}
TOTAL_MAX = sum(MAX.values())  # 9

# 인과 연결어. '면' 하나만으로는 '측면' 같은 단어에 걸려서 동사와 붙은 꼴만 본다
CONNECTIVES = re.compile(
    r"때문|그래서|따라서|그러므로|그러니|덕분|탓에|(?:으)?로 인해|이어지|이어져|이어질|영향|결과적으로|→"
    r"|(?:하|되|오르|내리|늘|줄|커지|작아지|높아지|낮아지|떨어지|올라가|내려가)면|므로|니까"
)
CONTRASTS = re.compile(r"하지만|그러나|다만|반면|반대로|그런데|위험|리스크|우려|변수|한계|못할 수|않을 수")
CONDITIONS = re.compile(r"만약|라면|다면|(?:는|은|할|인) 경우|경우에는|(?:하|되)면")
SENTENCE_SPLIT = re.compile(r"[.!?。\n]+")


@dataclass(frozen=True)
class RuleResult:
    rubric: dict[str, int]
    total: int
    score: int  # 0~100
    matched_facts: list[str]
    matched_concepts: list[str]


def _squash(s: str) -> str:
    """띄어쓰기 차이를 없앤다 ('기준 금리' == '기준금리')."""
    return re.sub(r"\s+", "", s).lower()


def _mentions(text: str, words: list[str]) -> bool:
    t = _squash(text)
    return any(w and _squash(w) in t for w in words)


def _concept_words(c: dict) -> list[str]:
    return [c["name"], *c.get("aliases", [])]


def score_evidence(text: str, key_facts: list[dict]) -> tuple[int, list[str]]:
    matched = [f["text"] for f in key_facts if _mentions(text, f.get("keywords", []))]
    if not matched:
        return 0, matched
    if len(matched) >= 2 and CONNECTIVES.search(text):
        return 2, matched
    return 1, matched


def score_reasoning(text: str, chain: list[dict]) -> tuple[int, list[str]]:
    matched = [c["name"] for c in chain if _mentions(text, _concept_words(c))]
    n_conn = len(CONNECTIVES.findall(text))
    if not matched:
        return 0, matched
    if len(matched) == 1:
        return 1, matched
    if n_conn == 0:
        return 2, matched
    if len(matched) >= 3 and n_conn >= 2:
        return 4, matched
    return 3, matched


def score_rebuttal(text: str, chain: list[dict], key_facts: list[dict]) -> int:
    """반대 표현이 있는 문장만 본다. 문장마다 점수를 매겨 가장 높은 값."""
    best = 0
    words = [w for c in chain for w in _concept_words(c)] + [w for f in key_facts for w in f.get("keywords", [])]
    for sent in SENTENCE_SPLIT.split(text):
        m = CONTRASTS.search(sent)
        if not m:
            continue
        after = sent[m.start():]  # 반대 표현 뒤에 다른 힘을 말했는지
        level = 1
        if _mentions(after, words):
            level = 2
            if CONDITIONS.search(after):
                level = 3
        best = max(best, level)
    return best


def to_score(total: int) -> int:
    """루브릭 합계(0~9) -> 100점 환산. 반올림 (6점 -> 67)."""
    total = max(0, min(TOTAL_MAX, total))
    return int(total * 100 / TOTAL_MAX + 0.5)


def grade(text: str, key_facts: list[dict], chain: list[dict]) -> RuleResult:
    evidence, facts = score_evidence(text, key_facts)
    reasoning, concepts = score_reasoning(text, chain)
    rebuttal = score_rebuttal(text, chain, key_facts)
    rubric = {"evidence": evidence, "reasoning": reasoning, "rebuttal": rebuttal}
    total = sum(rubric.values())
    return RuleResult(rubric, total, to_score(total), facts, concepts)
