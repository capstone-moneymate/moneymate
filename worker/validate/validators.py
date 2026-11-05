"""검증기 최소 버전 (B). LLM이 만든 인과 순서 문제를 개념 사전 계산 결과(concepts/graph.py)와 원문에 대조한다.
통과 여부는 코드가 정하고, 실패 이유(errors)는 그대로 출제 단계에 돌려줘 다시 쓰게 한다.

사용 예:
    from validate.validators import verify
    report = verify(quiz, source_text)
    report.passed     # True / False
    report.errors     # ["오르내림 방향이 개념 사전과 다름 (사전: 하락 압력, 퀴즈: 상승 압력)", ...]
    report.warnings   # 통과는 시키지만 사람이 확인할 것

입력 형식 (임시. C의 출제 결과 형식과 맞출 것)
- start_concept: 시작 개념 id. LLM이 원문에서 고름
- change: 시작 개념이 커지거나 일어났으면 up, 줄어들었으면 down (예: 파월 "인하를 서두르지 않겠다" = 인하 기대 down)
- end_concept: 결과 개념 id
- answer_order: 정답 순서 (개념 id 목록, 시작과 결과 포함)
- direction: 결과 방향. up 상승 압력 / down 하락 압력
- evidence_quote: 근거로 인용한 원문 문장. 요약 말고 원문 그대로

검사 순서
1. 필드: 위 필드가 다 있는가, change·direction 이 up / down 인가
2. 개념 id: 사전에 있는가 (없으면 경로 검사는 하지 않음)
3. 경로: 시작 → 결과 경로가 있는가 (없으면 순서·방향 검사는 하지 않음)
4. 모호성: 방향이 다른 경로가 함께 있으면 순서 문제로 부적합 (방향 검사는 하지 않음)
5. 정답 순서: 사전 경로 중 하나와 같은가. 경로가 여러 개면 통과시키되 경고를 붙인다 (원문 설명과 같은 경로인지는 사람이 확인)
6. 방향: 사전으로 계산한 방향과 같은가
7. 근거 인용: 원문에 그대로 있는가 (띄어쓰기·줄바꿈 차이는 무시)

카드 전체에 쓰는 검사 (DB 를 읽지 않는 순수 함수. C의 compose 가 검증 단계에서 부른다)
- find_banned(texts): 매수·매도 권유, 수익 예측 표현. 목록은 banned_terms.txt
- find_duplicates(new_texts, past_texts): 이미 출제한 문제와 거의 같은 문장. 예전 문제는 C가 steps 에서 읽어 넘긴다
"""
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from concepts.graph import AMBIGUOUS, DOWN, UP, Graph, effect, load_graph

BANNED_PATH = Path(__file__).with_name("banned_terms.txt")

FIELDS = ["start_concept", "change", "end_concept", "answer_order", "direction", "evidence_quote"]
LABEL = {UP: "상승 압력", DOWN: "하락 압력"}

_graph: Graph | None = None


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def _default_graph() -> Graph:
    global _graph
    if _graph is None:
        _graph = load_graph()
    return _graph


def _squash(text: str) -> str:
    return " ".join(text.split())


def verify(quiz: dict, source_text: str, g: Graph | None = None) -> Report:
    """퀴즈 하나를 검사한다. g 를 주지 않으면 db/seeds 개념 사전을 쓴다."""
    g = g or _default_graph()
    r = Report()

    missing = [k for k in FIELDS if not quiz.get(k)]
    if missing:
        r.errors.append(f"필드가 비어 있음: {', '.join(missing)}")
    for k in ("change", "direction"):
        if quiz.get(k) and quiz[k] not in (UP, DOWN):
            r.errors.append(f"{k} 는 up / down 중 하나여야 함: {quiz[k]}")

    quote = quiz.get("evidence_quote")
    if quote and _squash(quote) not in _squash(source_text):
        r.errors.append("인용한 근거가 원문에 없음 (요약하지 말고 원문 문장을 그대로 인용)")

    start, end, order = quiz.get("start_concept"), quiz.get("end_concept"), quiz.get("answer_order") or []
    unknown = sorted({c for c in [start, end, *order] if c and c not in g.out})
    if unknown:
        r.errors.append(f"개념 사전에 없는 개념: {', '.join(unknown)}")
    if not start or not end or unknown or quiz.get("change") not in (UP, DOWN):
        return r

    e = effect(g, start, end, quiz["change"])
    if e.direction is None:
        r.errors.append(f"개념 사전에 {start} → {end} 경로가 없음")
        return r
    if e.direction == AMBIGUOUS:
        r.errors.append(f"{start} → {end} 사이에 방향이 다른 경로가 함께 있어 순서 문제로 부적합")

    paths = [p for p, _ in e.paths]
    if order not in paths:
        r.errors.append("정답 순서가 개념 사전의 경로와 다름 (가능한 경로: "
                        + " / ".join(" → ".join(p) for p in paths) + ")")
    elif len(paths) > 1:
        r.warnings.append(f"{start} → {end} 경로가 {len(paths)}개라 원문 설명과 같은 경로인지 확인 필요")

    if e.direction != AMBIGUOUS and quiz.get("direction") in (UP, DOWN) and quiz["direction"] != e.direction:
        r.errors.append(f"오르내림 방향이 개념 사전과 다름 (사전: {LABEL[e.direction]}, 퀴즈: {LABEL[quiz['direction']]})")
    return r


# ------------------------------------------------------------------
# 금지 표현 (CLAUDE.md 10번). 목록은 banned_terms.txt
# ------------------------------------------------------------------

def parse_banned(lines: list[str]) -> list[re.Pattern]:
    """banned_terms.txt 줄 → 정규식. 빈 줄·# 주석은 건너뛰고, 띄어쓰기는 '있어도 없어도'(\\s*)로 바꾼다."""
    patterns = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(re.compile(r"\s*".join(line.split())))
    return patterns


@lru_cache(maxsize=1)
def _banned_patterns() -> tuple[re.Pattern, ...]:
    return tuple(parse_banned(BANNED_PATH.read_text(encoding="utf-8").splitlines()))


def find_banned(texts: list[str], patterns: list[re.Pattern] | None = None) -> list[str]:
    """문장들에서 걸린 금지 표현을 찾은 순서대로, 겹치지 않게 돌려준다. 없으면 빈 목록.

    출제 에이전트에게 "이 표현을 빼라"로 돌려주거나, 채점 피드백을 고정 문구로 바꿀지 정할 때 쓴다.
    """
    found: list[str] = []
    for text in texts:
        for p in patterns if patterns is not None else _banned_patterns():
            for m in p.finditer(text or ""):
                if m.group() not in found:
                    found.append(m.group())
    return found


# ------------------------------------------------------------------
# 중복 (이미 출제한 문제와 거의 같은 문장인가)
# ------------------------------------------------------------------

DUPLICATE_THRESHOLD = 90


def find_duplicates(new_texts: list[str], past_texts: list[str],
                    threshold: float = DUPLICATE_THRESHOLD) -> list[str]:
    """새 문제 문장마다 예전 문제 중 가장 비슷한 것과 비교해, threshold 이상이면 오류 문장을 돌려준다.

    유사도는 RapidFuzz ratio(문장 전체를 글자 단위로 비교, 0~100). 대소문자·문장부호는 무시한다.
    기술확정안의 token_set_ratio 는 짧은 문장이 긴 문장에 포함되기만 해도 100이 나와서 쓰지 않았다.
    "거의 같은 문장"만 잡는다. 말투만 바꾼 같은 질문(75점 안팎)은 잡지 못하고, 같은 틀에 종목·사건만 바꾼
    문제(86점 안팎)는 통과시킨다 (측정 예시는 docs/modules/validators.md).
    """
    from rapidfuzz import fuzz, process, utils  # 의존성 추가 전에도 다른 검사는 쓸 수 있게 여기서 불러온다

    past = [t for t in past_texts if t and t.strip()]
    errors = []
    for text in new_texts:
        if not text or not text.strip() or not past:
            continue
        match, score, _ = process.extractOne(text, past, scorer=fuzz.ratio, processor=utils.default_process)
        if score >= threshold:
            errors.append(f'"{text}" 가 예전 문제 "{match}" 와 거의 같아요 (유사도 {score:.0f}). 다른 질문으로 바꿔 주세요')
    return errors
