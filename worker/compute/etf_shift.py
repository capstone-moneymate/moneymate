"""ETF 전 종목 공통 이동 보정 (B, #141). 순수 함수라 DB 를 읽지 않는다.

1CU 기준 수량은 운용사가 종목을 고르지 않아도 전 종목이 같은 비율로 움직이는 날이 있다
(1CU 안 현금 비중 조정, 설정 단위 변경. findings.md B칸 「KoAct 설정 단위 경고 확인」).
그런 날을 "공통 이동일"로 찾아 그 비율(m)로 나눠 되돌리고, 운용사가 실제로 고른 매매만 남긴다.

공통 이동일 (그날과 바로 앞 스냅샷 비교)
1. 두 날 모두 있는 종목이 MIN_COMMON 개 이상
2. 종목별 수량비(오늘 ÷ 어제)의 중앙값 m 이 1 에서 MIN_MOVE 넘게 벗어남
3. 종목의 SHIFT_SHARE 이상이 m 의 ±SAME_TOL 안에서 같이 움직임
   (몇 종목은 그날 실제로 사고팔아 비율이 다를 수 있어 "모두"가 아니라 "대부분"으로 본다)

쓰는 곳
- compute/etf_trend.py: 추세(trend_chg_pct)는 기준일 이후 m 을 곱한 배수로, 전일 대비(day_chg_pct)는 그날 m 으로 나눈다
- compute/overlap.py (A, 후속 작업): 최신 수량을 common_shift 배수로 나눠 etf_change 에 넣는다
- collectors/etf_holdings.py: 수집할 때 공통 이동일이면 경고한다

손계산 (A 와 맞춘 예시): 기준 100주, 공통 이동일 m = 1.064
- 같이 밀린 종목 106.4 → 106.4 ÷ 1.064 = 100 → 추세 0%
- 그날 더 산 종목 110 → 110 ÷ 1.064 ≈ 103.38 → 추세 +3.4% (실제 매매만 남음)
"""
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from statistics import median

# 2026-11-17 B 결정 (#141). 3분기 KoAct 공통 이동일은 같이 움직인 종목 73~88%, TIME 은 공통 이동일 없음
SHIFT_SHARE = 0.7   # 이 비율 이상의 종목이 같은 비율로 움직여야 공통 이동일
SAME_TOL = 0.005    # 중앙값의 ±0.5% 안이면 "같은 비율" (KoAct 소수 수량 반올림 여유)
MIN_MOVE = 0.005    # 중앙값이 ±0.5% 넘게 움직여야 (그 아래는 반올림·잡음)
MIN_COMMON = 5      # 두 날 모두 있는 종목이 이보다 적으면 판단하지 않는다

Quantities = Mapping[str, Decimal | float | int]


@dataclass
class Shift:
    """기준일부터 최신일까지의 보정. factor 로 최신 수량을 나누면 공통 이동이 빠진다."""
    factor: float = 1.0                                       # 공통 이동일 m 을 모두 곱한 값 (없으면 1)
    days: list[date] = field(default_factory=list)            # 공통 이동으로 본 날짜 (뒤 날짜 기준)
    ratios: dict[date, float] = field(default_factory=dict)   # 날짜 -> 그날 m


def day_shift(prev: Quantities, curr: Quantities) -> float | None:
    """하루 비교에서 공통 이동이면 그 비율 m, 아니면 None."""
    common = [k for k in curr if k in prev and prev[k] and prev[k] > 0]
    if len(common) < MIN_COMMON:
        return None
    # 비교는 Decimal 로 한다. float 이면 100 → 99.5 (정확히 −0.5%) 가 0.0050000000000000044 가 되어 경계를 넘는다
    ratios = [_dec(curr[k]) / _dec(prev[k]) for k in common]
    m = median(ratios)
    if abs(m - 1) <= _dec(MIN_MOVE):
        return None
    together = sum(abs(r / m - 1) <= _dec(SAME_TOL) for r in ratios)
    return float(m) if Decimal(together) / len(ratios) >= _dec(SHIFT_SHARE) else None


def _dec(x: Decimal | float | int) -> Decimal:
    """float 는 문자열로 거쳐 0.005 가 0.005000000000000000104... 가 되지 않게 한다."""
    return x if isinstance(x, Decimal) else Decimal(str(x))


def common_shift(snapshots: Mapping[date, Quantities]) -> Shift:
    """날짜별 스냅샷(기준일부터 최신일까지) → 보정 배수와 공통 이동일.

    날짜 순서대로 바로 앞 스냅샷과 비교한다. 첫 날짜(기준일)는 비교 대상이 없어 공통 이동일이 될 수 없다.
    수집을 빠뜨린 날이 있으면 그 앞 스냅샷과 비교한다 (etf_trend 의 전일과 같다).
    """
    out = Shift()
    dates = sorted(snapshots)
    for prev_d, d in zip(dates, dates[1:]):
        m = day_shift(snapshots[prev_d], snapshots[d])
        if m is not None:
            out.factor *= m
            out.days.append(d)
            out.ratios[d] = m
    return out


def adjust(quantity: Decimal | None, factor: float) -> Decimal | None:
    """수량을 보정 배수로 나눈다. 배수가 1 이면 그대로 (Decimal 그대로라 기존 계산과 같은 값)."""
    if quantity is None or factor == 1.0:
        return quantity
    return Decimal(quantity) / Decimal(str(factor))
