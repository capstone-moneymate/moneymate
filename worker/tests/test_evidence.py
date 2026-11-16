"""validators.check_evidence 테스트 (근거 날짜, 탭 2). 기준일은 3분기 13F 분기 말 2026-09-30."""
from datetime import date

import pytest

from validate.validators import check_evidence

BASE = date(2026, 9, 30)
# 입력으로 넘긴 근거 3개: 1번 기준일 당일, 2번 기준일 전, 3번 기준일 다음 날
AVAILABLE = {1: "2026-09-30", 2: "2026-08-14", 3: "2026-10-01"}


def test_passes_when_all_before_or_on_base_date():
    # 기준일 당일(9/30)도 통과: 13F 는 분기 말 보유를 보여 주므로 그날 자료까지 쓸 수 있다
    assert check_evidence([1, 2], AVAILABLE, BASE) == []


def test_after_base_date_fails():
    assert check_evidence([3], AVAILABLE, BASE) == ["근거 3 는 공시 기준일(2026-09-30) 뒤에 나온 자료예요"]


def test_empty_choice_fails():
    assert check_evidence([], AVAILABLE, BASE) == ["근거 자료 번호를 1개 이상 고르세요"]


def test_number_not_in_input_fails():
    assert check_evidence([2, 7], AVAILABLE, BASE) == ["입력에 없는 근거 번호예요: 7"]


def test_non_int_number_fails():
    # "2" 문자열, True(= int 1 로 읽힐 수 있음)는 번호로 치지 않는다
    assert check_evidence(["2", True], AVAILABLE, BASE) == [
        "입력에 없는 근거 번호예요: 2",
        "입력에 없는 근거 번호예요: True",
    ]


def test_duplicate_number_fails_once():
    # 2를 세 번: 두 번째·세 번째마다 한 줄씩
    assert check_evidence([2, 2, 2], AVAILABLE, BASE) == [
        "근거 2 를 두 번 골랐어요. 한 번만 쓰세요",
        "근거 2 를 두 번 골랐어요. 한 번만 쓰세요",
    ]


def test_several_errors_in_order_with_where():
    out = check_evidence([3, 9, 1, 1], AVAILABLE, BASE, where="이유 2")
    assert out == [
        "이유 2: 근거 3 는 공시 기준일(2026-09-30) 뒤에 나온 자료예요",
        "이유 2: 입력에 없는 근거 번호예요: 9",
        "이유 2: 근거 1 를 두 번 골랐어요. 한 번만 쓰세요",
    ]


def test_accepts_date_objects_and_string_base_date():
    available = {1: date(2026, 9, 29), 2: date(2026, 10, 2)}
    assert check_evidence([1, 2], available, "2026-09-30") == [
        "근거 2 는 공시 기준일(2026-09-30) 뒤에 나온 자료예요"
    ]


def test_empty_input_means_every_number_is_unknown():
    assert check_evidence([1], {}, BASE) == ["입력에 없는 근거 번호예요: 1"]


@pytest.mark.parametrize("bad", ["2026/09/30", "20260930", "2026-9-30", "2026-02-30", None])
def test_bad_date_format_raises(bad):
    # 입력 데이터 문제는 LLM 이 고칠 수 없으니 오류 문장이 아니라 예외
    with pytest.raises(ValueError):
        check_evidence([1], {1: bad}, BASE)
    with pytest.raises(ValueError):
        check_evidence([1], {1: "2026-09-01"}, bad)


def test_same_messages_as_reasons_check():
    """reasons.check_reasons 의 근거 검사와 같은 문장인지 (C가 바꿔 끼울 때 기존 테스트가 그대로 통과하게)."""
    from generate.reasons import Evidence, check_reasons
    from concepts.graph import load_graph

    evidence = [
        Evidence(no=1, source_id=10, published_date="2026-09-12", title="a", issuer_name=None, url="u"),
        Evidence(no=2, source_id=11, published_date="2026-10-03", title="b", issuer_name=None, url="u"),
    ]
    raw = [{"title": "t", "body": "b", "start_concept": "x", "end_concept": "x", "evidence": [2, 5]}]
    old = [e for e in check_reasons(raw, evidence, BASE, load_graph()) if "근거" in e]
    new = check_evidence([2, 5], {e.no: e.published_date for e in evidence}, BASE, where="이유 1")
    assert new == old
