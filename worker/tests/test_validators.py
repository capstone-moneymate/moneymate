import pytest

from concepts.graph import build_graph
from validate.validators import verify

# 손계산용 작은 사전 (test_graph.py 와 같은 파월 예시 + 모호성 예시 + 경로 2개 예시)
NAMES = {c: c for c in ["cut_expect", "rate_long", "pv", "growth", "x", "y", "w", "z", "hike", "yield", "val"]}
EDGES = [
    ("cut_expect", "rate_long", "down"), ("rate_long", "pv", "down"), ("pv", "growth", "up"),
    ("x", "y", "up"), ("y", "z", "up"), ("x", "w", "up"), ("w", "z", "down"),   # 모호: + / -
    ("hike", "val", "down"), ("hike", "yield", "up"), ("yield", "val", "down"),  # 경로 2개, 둘 다 -
]
SOURCE = "파월 의장은 \"금리 인하를 서두르지 않겠다\"고 말했다.\n시장은 연내 인하 기대를 낮췄다."


@pytest.fixture
def g():
    return build_graph(NAMES, EDGES)


def powell(**override):
    # 인하 기대 줄어듦(down) → (-1)×(-1)×(+1)×(-1) = -1 → 성장주 하락 압력
    quiz = {
        "start_concept": "cut_expect", "change": "down", "end_concept": "growth",
        "answer_order": ["cut_expect", "rate_long", "pv", "growth"],
        "direction": "down",
        "evidence_quote": "파월 의장은 \"금리 인하를 서두르지 않겠다\"고 말했다.",
    }
    quiz.update(override)
    return quiz


def test_valid_quiz_passes(g):
    r = verify(powell(), SOURCE, g)
    assert r.passed and r.errors == [] and r.warnings == []


def test_wrong_direction(g):
    r = verify(powell(direction="up"), SOURCE, g)
    assert r.errors == ["오르내림 방향이 개념 사전과 다름 (사전: 하락 압력, 퀴즈: 상승 압력)"]


def test_change_flips_direction(g):
    # 인하 기대가 커지면(up) 성장주 상승 압력 → direction up 이 정답
    assert verify(powell(change="up", direction="up"), SOURCE, g).passed
    assert not verify(powell(change="up", direction="down"), SOURCE, g).passed


def test_wrong_order(g):
    r = verify(powell(answer_order=["cut_expect", "pv", "rate_long", "growth"]), SOURCE, g)
    assert len(r.errors) == 1 and r.errors[0].startswith("정답 순서가 개념 사전의 경로와 다름")


def test_quote_not_in_source(g):
    r = verify(powell(evidence_quote="파월은 금리를 올리겠다고 말했다."), SOURCE, g)
    assert r.errors == ["인용한 근거가 원문에 없음 (요약하지 말고 원문 문장을 그대로 인용)"]


def test_quote_ignores_spacing(g):
    # 줄바꿈·띄어쓰기 차이만 있으면 같은 문장으로 본다
    assert verify(powell(evidence_quote="말했다.  시장은 연내\n인하 기대를"), SOURCE, g).passed


def test_ambiguous_pair_rejected(g):
    r = verify({"start_concept": "x", "change": "up", "end_concept": "z", "answer_order": ["x", "y", "z"],
                "direction": "up", "evidence_quote": "시장은"}, SOURCE, g)
    assert r.errors == ["x → z 사이에 방향이 다른 경로가 함께 있어 순서 문제로 부적합"]


def test_multiple_paths_pass_with_warning(g):
    # hike → val 은 직접 / yield 경유 2개, 둘 다 하락 압력. 어느 쪽이든 통과, 경고만
    quiz = {"start_concept": "hike", "change": "up", "end_concept": "val", "answer_order": ["hike", "yield", "val"],
            "direction": "down", "evidence_quote": "시장은"}
    r = verify(quiz, SOURCE, g)
    assert r.passed
    assert r.warnings == ["hike → val 경로가 2개라 원문 설명과 같은 경로인지 확인 필요"]


def test_no_path(g):
    r = verify(powell(start_concept="growth", end_concept="cut_expect", answer_order=["growth", "cut_expect"]),
               SOURCE, g)
    assert r.errors == ["개념 사전에 growth → cut_expect 경로가 없음"]


def test_unknown_concept(g):
    r = verify(powell(answer_order=["cut_expect", "missing", "growth"]), SOURCE, g)
    assert r.errors == ["개념 사전에 없는 개념: missing"]


def test_missing_and_bad_fields(g):
    r = verify(powell(evidence_quote="", direction="sideways"), SOURCE, g)
    assert "필드가 비어 있음: evidence_quote" in r.errors
    assert "direction 는 up / down 중 하나여야 함: sideways" in r.errors


def test_seed_dictionary():
    # 실제 개념 사전 (db/seeds): 인하 → 국채 금리 ▼ → 성장주 ▲
    quiz = {"start_concept": "rate_cut", "change": "up", "end_concept": "growth_valuation",
            "answer_order": ["rate_cut", "bond_yield", "growth_valuation"],
            "direction": "up", "evidence_quote": "기준금리를 0.25%p 인하했다"}
    assert verify(quiz, "한국은행은 기준금리를 0.25%p 인하했다.").passed


# ---- 인과 순서 문제는 개념 3개 이상 (#178) ----

def test_two_concept_order_fails_even_if_it_is_a_path(g):
    # hike → val 은 사전의 직접 연결이라 경로지만 개념 2개뿐 → 순서 맞추기가 아니라 고르기
    quiz = {"start_concept": "hike", "change": "up", "end_concept": "val", "answer_order": ["hike", "val"],
            "direction": "down", "evidence_quote": "시장은 연내 인하 기대를 낮췄다."}
    errors = verify(quiz, SOURCE, g).errors
    assert errors == ["정답 순서는 개념 3개 이상이어야 함 (지금 2개). find_concept_path 결과에서 개념 3개 이상인 경로를 고르세요"]
    # 같은 쌍의 3개짜리 경로(hike → yield → val)는 통과 (경로 2개라 경고만)
    r = verify({**quiz, "answer_order": ["hike", "yield", "val"]}, SOURCE, g)
    assert r.errors == [] and len(r.warnings) == 1


def test_order_starts_small_dictionary(g):
    from validate.validators import order_starts
    # cut_expect(4개)·hike(3개)는 가능. x 는 x → z 가 모호하지만 x → y → z 가 아니라 x → y(2개)·x → w(2개)뿐이라 불가
    # rate_long → pv → growth (3개) 도 가능
    assert order_starts(g) == {"cut_expect", "rate_long", "hike"}


def test_order_starts_real_dictionary():
    # 2026-11-19 실제 사전: 3칸 이상 경로가 있는 시작 개념 9개. 동결·기업 실적 등은 2칸까지라 빠진다
    from validate.validators import order_starts
    assert order_starts() == {"ai_investment", "buyback", "gpu_demand", "hbm_demand", "hbm_supply", "inflation",
                              "rate_cut", "rate_hike", "supply_contract_win"}
