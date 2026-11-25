"""learner/bkt.py 손계산 테스트 (사람2, 계획 2-3). DB·API 없음.
기본값은 처음 0.25, 배움 0.2, 실수 0.1 (2026-11-25 에 처음 0.3·배움 0.1 에서 바꿈. 근거는 docs/modules/learner_bkt.md)."""
import pytest

from learner import bkt


def test_correct_matches_hand_calc():
    # 0.225 / (0.225 + 0.1875) = 0.5455, 배움 0.2 → 0.5455 + 0.4545 × 0.2 = 0.6364
    assert bkt.posterior(0.25, True, 0.25) == pytest.approx(0.225 / 0.4125)
    assert bkt.update(0.25, True, 0.25) == pytest.approx(0.6364, abs=1e-4)


def test_wrong_matches_hand_calc():
    # 0.025 / (0.025 + 0.5625) = 0.0426, 배움 0.2 → 0.0426 + 0.9574 × 0.2 = 0.2340
    assert bkt.posterior(0.25, False, 0.25) == pytest.approx(0.025 / 0.5875)
    assert bkt.update(0.25, False, 0.25) == pytest.approx(0.2340, abs=1e-4)


def test_repeated_correct_reaches_know():
    # 0.25 → 0.64 → 0.89 → 0.97: 4지선다는 세 번 연달아 맞혀야 0.95 를 넘는다
    p, seen = bkt.DEFAULT.p_init, []
    for _ in range(3):
        p = bkt.update(p, True, 0.25)
        seen.append(round(p, 2))
    assert seen == [0.64, 0.89, 0.97]
    assert bkt.corrects_to_know(0.25) == 3
    assert bkt.corrects_to_know(1 / 3) == 4      # 3지선다 (복습 문제의 용어 뜻·틀린 설명)


def test_easier_to_guess_means_weaker_evidence():
    # O/X(추측 0.5)를 맞힌 것은 칩 빈칸(추측 0.08)을 맞힌 것보다 덜 올린다
    ox, chips = bkt.update(0.25, True, 0.5), bkt.update(0.25, True, 1 / 12)
    assert ox < bkt.update(0.25, True, 0.25) < chips
    # 0.225 / (0.225 + 0.375) = 0.375 → 0.375 + 0.625 × 0.2 = 0.5
    assert ox == pytest.approx(0.5)
    assert bkt.corrects_to_know(0.5) == 5
    assert bkt.corrects_to_know(1 / 12) == 2


def test_wrong_after_know_drops_but_not_to_zero():
    # 0.95 에서 한 번 틀림: 0.095 / (0.095 + 0.0375) = 0.717 → 0.717 + 0.283 × 0.2 = 0.774 (실수일 수 있으니 바닥까지 안 내린다)
    assert bkt.update(0.95, False, 0.25) == pytest.approx(0.7736, abs=1e-4)


def test_never_drops_below_learn_rate():
    # 계속 틀려도 알 확률은 배울 확률(0.2) 아래로 내려가지 않는다: 베이즈 갱신이 0 에 가까워져도 배움 반영이 0.2 를 더한다
    p = bkt.DEFAULT.p_init
    for _ in range(10):
        p = bkt.update(p, False, 1 / 3)
        assert p >= bkt.DEFAULT.p_learn
    assert p == pytest.approx(0.2353, abs=1e-4)


def test_old_and_new_defaults_need_almost_the_same_corrects():
    # 민감도: 2026-11-25 에 바꾸기 전 값(처음 0.3, 배움 0.1)과 지금 값의 "안다"까지 연달아 맞힐 횟수. O/X 만 한 번 다르다
    old = bkt.Params(p_init=0.3, p_learn=0.1)
    got = {g: (bkt.corrects_to_know(g, old), bkt.corrects_to_know(g)) for g in (1 / 12, 0.25, 1 / 3, 0.5)}
    assert got == {1 / 12: (2, 2), 0.25: (3, 3), 1 / 3: (4, 4), 0.5: (6, 5)}


def test_guess_zero_does_not_lock_at_one():
    p = bkt.update(0.3, True, 0.0)   # 추측 0 은 0.01 로 올려 쓴다
    assert p < 1
    assert bkt.update(p, False, 0.0) < p


def test_guess_clamped_to_range():
    assert bkt.clamp_guess(0.0) == bkt.GUESS_MIN
    assert bkt.clamp_guess(0.9) == bkt.GUESS_MAX
    assert bkt.update(0.3, True, 0.9) == bkt.update(0.3, True, 0.5)


def test_stays_in_range():
    for p in (0.0, 0.001, 0.5, 0.999, 1.0):
        for correct in (True, False):
            for g in (0.0, 0.06, 0.25, 0.5):
                assert 0 <= bkt.update(p, correct, g) <= 1


def test_params_change_result():
    # 민감도 분석: 배움을 0 으로 두면 베이즈 갱신 값 그대로
    no_learn = bkt.Params(p_learn=0.0)
    assert bkt.update(0.25, True, 0.25, no_learn) == pytest.approx(0.225 / 0.4125)
    # 실수를 0.05 로 줄이면 맞힘의 증거가 조금 더 세다
    assert bkt.update(0.3, True, 0.25, bkt.Params(p_slip=0.05)) > bkt.update(0.3, True, 0.25)
    # 처음 알 확률이 낮으면 더 많이 맞혀야 한다
    assert bkt.corrects_to_know(0.25, bkt.Params(p_init=0.1)) >= bkt.corrects_to_know(0.25)


def test_bad_values_rejected():
    with pytest.raises(ValueError):
        bkt.update(1.2, True, 0.25)
    with pytest.raises(ValueError):
        bkt.Params(p_slip=1.0)
