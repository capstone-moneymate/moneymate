"""learner/calibration.py 손계산 테스트 (사람2, 계획 2-5). DB 없음."""
import pytest

from learner import calibration as cal


def test_hand_calc_twenty_answers():
    # 확실+맞힘 9, 확실+틀림 3, 헷갈려요+맞힘 3, 헷갈려요+틀림 5
    s = cal.summarize(cal.Table(sure_right=9, sure_wrong=3, unsure_right=3, unsure_wrong=5))
    assert s["total"] == 20 and s["enough"] is True
    assert s["sensitivity"] == pytest.approx(9 / 12)        # 맞힌 12개 중 확실해요 9개
    assert s["specificity"] == pytest.approx(5 / 8)         # 틀린 8개 중 헷갈려요 5개
    assert s["illusion"] == pytest.approx(3 / 8)            # 틀린 8개 중 확실해요 3개 (착각)
    assert s["sure_accuracy"] == pytest.approx(0.75)        # 확실해요 12개 중 9개 맞힘
    assert s["unsure_accuracy"] == pytest.approx(0.375)     # 헷갈려요 8개 중 3개 맞힘
    assert s["gap"] == pytest.approx(0.375)
    assert s["gamma"] == pytest.approx(36 / 54)             # (9·5 - 3·3) / (9·5 + 3·3)
    assert s["bias"] == pytest.approx(0.0)                  # 확실해요 12/20 - 정답 12/20


def test_perfect_monitoring():
    s = cal.summarize(cal.Table(sure_right=12, unsure_wrong=8))
    assert (s["sensitivity"], s["specificity"], s["illusion"], s["gamma"], s["bias"]) == (1.0, 1.0, 0.0, 1.0, 0.0)


def test_overconfident_is_positive_bias():
    # 전부 확실해요라고 했는데 절반만 맞음: 확실해요 20/20 - 정답 10/20 = +0.5
    over = cal.summarize(cal.Table(sure_right=10, sure_wrong=10))
    assert over["bias"] == pytest.approx(0.5) and over["illusion"] == 1.0
    assert over["unsure_accuracy"] is None and over["gap"] is None and over["gamma"] is None
    # 전부 헷갈려요라고 했는데 대부분 맞음: 과소확신
    under = cal.summarize(cal.Table(unsure_right=16, unsure_wrong=4))
    assert under["bias"] == pytest.approx(-0.8) and under["sensitivity"] == 0.0


def test_confidence_unrelated_to_correctness_is_zero_gamma():
    s = cal.summarize(cal.Table(sure_right=6, sure_wrong=4, unsure_right=6, unsure_wrong=4))
    assert s["gamma"] == pytest.approx(0.0) and s["gap"] == pytest.approx(0.0)


def test_inverted_confidence_is_negative_gamma():
    s = cal.summarize(cal.Table(sure_right=2, sure_wrong=8, unsure_right=8, unsure_wrong=2))
    assert s["gamma"] == pytest.approx((4 - 64) / (4 + 64))
    assert s["gap"] == pytest.approx(0.2 - 0.8)


def test_missing_cells_give_none_not_error():
    empty = cal.summarize(cal.Table())
    assert empty["total"] == 0 and empty["enough"] is False
    assert all(empty[k] is None for k in ("sensitivity", "specificity", "illusion", "sure_accuracy", "gamma", "bias"))
    no_wrong = cal.summarize(cal.Table(sure_right=5, unsure_right=2))       # 틀린 답이 없으면 착각률을 알 수 없다
    assert no_wrong["specificity"] is None and no_wrong["illusion"] is None
    assert no_wrong["sensitivity"] == pytest.approx(5 / 7)


def test_enough_threshold():
    assert cal.summarize(cal.Table(sure_right=19))["enough"] is False
    assert cal.summarize(cal.Table(sure_right=20))["enough"] is True


def test_negative_count_rejected():
    with pytest.raises(ValueError):
        cal.Table(sure_right=-1)


def test_brier_hand_calc():
    # (0.9-1)² + (0.6-0)² + (0.3-0)² + (0.8-1)² = 0.01 + 0.36 + 0.09 + 0.04 = 0.5 → 평균 0.125
    assert cal.brier([0.9, 0.6, 0.3, 0.8], [True, False, False, True]) == pytest.approx(0.125)
    assert cal.brier([0.5, 0.5], [True, False]) == pytest.approx(0.25)      # 늘 반반이라고 하면 0.25
    assert cal.brier([1.0, 0.0], [True, False]) == 0.0
    assert cal.brier([], []) is None
    with pytest.raises(ValueError):
        cal.brier([0.5], [True, False])
    with pytest.raises(ValueError):
        cal.brier([1.2], [True])
