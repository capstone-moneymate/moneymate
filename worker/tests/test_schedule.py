"""learner/schedule.py 테스트 (사람2, 계획 2-4). DB 없음. 기대값은 FSRS-6 기본 가중치로 손계산한 값이다."""
from datetime import datetime, timedelta, timezone

import pytest
from fsrs import Rating

from learner import schedule as sc

T0 = datetime(2026, 11, 24, 9, 0, tzinfo=timezone.utc)


# ---------- 자동 평가 ----------

def test_wrong_is_again_whatever_else():
    assert sc.rate(False) == Rating.Again
    assert sc.rate(False, confidence=2, fast=True, answer_changes=0) == Rating.Again


def test_correct_follows_confidence():
    assert sc.rate(True, confidence=1) == Rating.Hard
    assert sc.rate(True, confidence=2) == Rating.Good
    assert sc.rate(True) == Rating.Good                       # 확신 없이 온 답 (판단해보기, 예전 화면)


def test_easy_needs_every_signal():
    assert sc.rate(True, confidence=2, fast=True, answer_changes=0) == Rating.Easy
    assert sc.rate(True, confidence=2, fast=True) == Rating.Easy             # 답 변경을 안 잰 경우
    assert sc.rate(True, confidence=2, fast=True, answer_changes=1) == Rating.Good   # 답을 바꿨으면 망설인 것
    assert sc.rate(True, confidence=2, fast=False, answer_changes=0) == Rating.Good
    assert sc.rate(True, confidence=1, fast=True, answer_changes=0) == Rating.Hard   # 헷갈렸으면 빨라도 Hard


def test_confidence_accepts_screen_words():
    assert sc.normalize_confidence("확실해요") == sc.normalize_confidence("확신해요") == 2
    assert sc.normalize_confidence("헷갈려요") == sc.normalize_confidence("애매해요") == 1
    assert sc.normalize_confidence(None) is None
    with pytest.raises(ValueError):
        sc.normalize_confidence(3)


def test_is_fast_uses_own_fastest_quarter():
    past = [4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000]   # 8개 → 빠른 쪽 1/4 = 4초, 5초
    assert sc.is_fast(5000, past) is True
    assert sc.is_fast(5001, past) is False
    assert sc.is_fast(None, past) is False
    assert sc.is_fast(1000, past[:7]) is False                  # 기록이 8개보다 적으면 시간은 안 본다


# ---------- 일정 ----------

@pytest.mark.parametrize("rating, stability, days", [
    (Rating.Again, 0.212, 1), (Rating.Hard, 1.2931, 1), (Rating.Good, 2.3065, 2), (Rating.Easy, 8.2956, 8)])
def test_first_review_hand_calc(rating, stability, days):
    m = sc.review(None, rating, T0)
    assert m.stability == pytest.approx(stability)             # 처음 안정도 = 평가별 가중치
    assert m.due - T0 == timedelta(days=days)                  # 안정도를 반올림한 날 수, 최소 1일
    assert m.last_review == T0


def test_first_difficulty_hand_calc():
    # 처음 난이도 = w4 - e^(w5 × (평가 - 1)) + 1.  Good: 6.4133 - e^(0.8334 × 2) + 1 = 2.118, Again: 6.4133
    assert sc.review(None, Rating.Good, T0).difficulty == pytest.approx(2.118, abs=1e-3)
    assert sc.review(None, Rating.Again, T0).difficulty == pytest.approx(6.4133, abs=1e-4)


def test_retrievability_is_90_percent_after_stability_days():
    # 안정도가 10일인 개념은 10일 뒤 기억 확률이 정확히 0.9 (안정도의 뜻)
    ten = sc.Memory(stability=10.0, difficulty=5.0, last_review=T0, due=T0 + timedelta(days=10))
    assert sc.retrievability(ten, T0) == pytest.approx(1.0)
    assert sc.retrievability(ten, T0 + timedelta(days=10)) == pytest.approx(0.9, abs=1e-9)
    # 처음 Good (안정도 2.3065일): 2일 뒤 (1 + 0.9804 × 2 / 2.3065)^(-0.1542) = 0.9095. 지난 시간은 날 단위로 센다
    m = sc.review(None, Rating.Good, T0)
    assert sc.retrievability(m, T0 + timedelta(days=2)) == pytest.approx(0.9095, abs=1e-4)
    assert sc.retrievability(m, T0 + timedelta(days=2, hours=23)) == pytest.approx(0.9095, abs=1e-4)
    assert sc.retrievability(m, T0 + timedelta(days=7)) < 0.85                # 쉬면 계속 내려간다


def test_intervals_grow_when_remembered_and_shrink_when_forgotten():
    m, t, gaps = None, T0, []
    for rating in (Rating.Good, Rating.Good, Rating.Good, Rating.Again, Rating.Good):
        m = sc.review(m, rating, t)
        gaps.append((m.due - t).days)
        t = m.due
    assert gaps == [2, 11, 46, 3, 8]      # 맞힐수록 길어지고, 틀리면 짧아졌다가 다시 길어진다


def test_easy_concept_waits_longer_than_hard_one():
    easy = sc.review(sc.review(None, Rating.Easy, T0), Rating.Easy, T0 + timedelta(days=8))
    hard = sc.review(sc.review(None, Rating.Hard, T0), Rating.Hard, T0 + timedelta(days=1))
    assert (easy.due - easy.last_review) > (hard.due - hard.last_review)
    assert easy.difficulty < hard.difficulty


def test_same_input_same_schedule():
    # 날짜를 흩뜨리는 기능(fuzzing)을 꺼서 돌릴 때마다 같다
    assert sc.review(None, Rating.Good, T0) == sc.review(None, Rating.Good, T0)


def test_naive_time_rejected():
    with pytest.raises(ValueError):
        sc.review(None, Rating.Good, datetime(2026, 11, 24, 9, 0))
