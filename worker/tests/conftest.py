"""모든 테스트 공통 설정."""
import pytest

from concepts import regime


@pytest.fixture(autouse=True)
def offline_regime(monkeypatch):
    """출제(compose)가 국면을 정하려고 FRED 를 부르지 않게 한다 (#174). 기본은 지표 0.00 = 평상시.
    국면을 바꿔 보는 테스트는 compose(..., regime=) 로 직접 넘기거나 이 함수를 다시 바꿔 끼운다."""
    from datetime import date

    monkeypatch.setattr(regime, "fetch_sahm", lambda as_of: [(date(2000, 1, 1), 0.0)])
    regime.regime_for_month.cache_clear()
    yield
    regime.regime_for_month.cache_clear()
