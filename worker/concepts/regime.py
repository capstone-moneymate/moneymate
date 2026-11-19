"""경기 국면 판정 (B, #174). 개념 사전의 국면별 조건부 연결(#158, db/seeds/cond_edges.csv)을 실제 출제·검증에 쓰려고
"지금 국면"을 데이터와 코드로 정한다. LLM 은 판단하지 않는다 (B 가 사람이 정하기·LLM 판단 대신 지표 방식으로 결정, 2026-11-19).

기준: 삼의 법칙(Sahm rule) 실시간 지표, FRED SAHMREALTIME (매달 숫자 하나, %p).
  실업률 3개월 평균이 지난 12개월의 3개월 평균 최저치보다 얼마나 올랐는지. 0.5 이상이면 경기 침체 신호.
  FRED 가 계산해 주는 값을 그대로 받고, 우리 코드는 0.5 와 비교만 한다.

판정
- 생성일이 속한 달보다 앞 달의 값 중 가장 최근 것을 쓴다. 그달 값은 다음 달 초에 발표되므로
  같은 달 값을 쓰면 지난 날짜로 카드를 다시 만들 때 그때는 몰랐던 값을 보게 된다.
- 값 ≥ 0.5 이면 recession, 아니면 normal. 값은 소수 둘째 자리라 반올림해서 비교한다 (0.5 경계를 float 오차로 놓치지 않게).
- 지표를 받지 못하면 평상시(normal)로 두고 까닭을 source 에 남긴다. 국면 때문에 출제가 멈추지 않게 하려는 것이다.

실행 (worker/ 에서):
    python -m concepts.regime                    # 오늘 기준 국면
    python -m concepts.regime --date 2024-09-15  # 그날 기준 국면

주의: 미국 지표다. 지금 사전의 조건부 연결(국채 금리 → 성장주 가치평가)도 미국 성장주 이야기라 맞지만,
국내 뉴스 카드에도 같은 국면을 쓴다. 2024년 7~9월처럼 지표가 0.5 를 넘었는데 실제 침체로 이어지지 않은 때도 있다.
"""
import argparse
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from functools import lru_cache

from concepts.graph import NORMAL

SAHM_SERIES = "SAHMREALTIME"
SAHM_THRESHOLD = 0.5
RECESSION = "recession"          # db/seeds/cond_edges.csv 의 국면 이름과 같다
LOOKBACK_DAYS = 400               # 가장 최근 발표 값을 찾으려고 넉넉히 받는다


@dataclass(frozen=True)
class Regime:
    """정한 국면과 근거. 카드 model_info.regime 에 to_json() 그대로 남긴다."""
    name: str                     # normal / recession
    sahm: float | None = None     # 쓴 달의 지표 값 (%p)
    observed: str | None = None   # 그 값의 달 (YYYY-MM-01, FRED 표기)
    source: str = f"FRED {SAHM_SERIES}"

    def to_json(self) -> dict:
        return asdict(self)


def regime_of(sahm: float) -> str:
    """지표 값 → 국면. 0.5 이상이면 recession."""
    return RECESSION if round(sahm, 2) >= SAHM_THRESHOLD else NORMAL


def latest_before_month(series: list[tuple[date, float]], as_of: date) -> tuple[date, float] | None:
    """as_of 가 속한 달보다 앞 달의 값 중 가장 최근 것. 없으면 None."""
    first_of_month = as_of.replace(day=1)
    usable = [(d, v) for d, v in series if d < first_of_month]
    return max(usable) if usable else None


def fetch_sahm(as_of: date) -> list[tuple[date, float]]:
    """FinanceDataReader 로 FRED SAHMREALTIME 을 받는다. 키 필요 없음 (collectors/sources.py 의 금리와 같은 방법)."""
    import FinanceDataReader as fdr

    df = fdr.DataReader(f"FRED:{SAHM_SERIES}", (as_of - timedelta(days=LOOKBACK_DAYS)).isoformat(),
                        as_of.isoformat()).dropna()
    return [(ts.date(), float(v)) for ts, v in df[SAHM_SERIES].items()]


def current_regime(as_of: date | None = None, fetch=None) -> Regime:
    """as_of(기본 오늘) 기준 국면. 지표를 받지 못하거나 값이 없으면 normal 과 까닭.
    fetch 를 주지 않으면 부를 때 이 모듈의 fetch_sahm 을 찾는다 (테스트가 바꿔 끼울 수 있게)."""
    as_of = as_of or date.today()
    try:
        series = (fetch or globals()["fetch_sahm"])(as_of)
    except Exception as e:  # noqa: BLE001  네트워크·형식 오류 모두 평상시로 (출제를 멈추지 않는다)
        return Regime(NORMAL, source=f"FRED {SAHM_SERIES} 를 받지 못해 평상시로 둠: {e.__class__.__name__}")
    found = latest_before_month(series, as_of)
    if found is None:
        return Regime(NORMAL, source=f"FRED {SAHM_SERIES} 에 {as_of:%Y-%m} 앞 달 값이 없어 평상시로 둠")
    observed, value = found
    return Regime(regime_of(value), round(value, 2), observed.isoformat())


@lru_cache(maxsize=16)
def regime_for_month(year: int, month: int) -> Regime:
    """그 달 카드에 쓸 국면. 같은 달이면 판정이 같아(앞 달 값만 씀) 출제 한 번 실행 안에서 FRED 를 한 번만 부른다.
    받기에 실패한 결과도 그 실행 동안은 다시 묻지 않는다 (카드마다 국면이 달라지지 않게)."""
    return current_regime(date(year, month, 1))


def prompt_note(r: Regime) -> str | None:
    """출제 에이전트에게 알려 줄 한 줄. 평상시면 None (예전 프롬프트 그대로)."""
    if r.name == NORMAL:
        return None
    return (f"지금은 경기 침체 국면이에요 ({r.source} {r.observed[:7]} = {r.sahm:.2f}, 기준 {SAHM_THRESHOLD} 이상). "
            "find_concept_path·validate_causal_order 는 이 국면의 연결로 계산하니, 해설도 그 결과대로 쓰고 "
            "평상시와 방향이 다른 연결이면 경기 침체 국면이라서라고 밝혀 주세요.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="삼의 법칙 지표로 경기 국면 판정")
    parser.add_argument("--date", help="기준일 YYYY-MM-DD (기본 오늘)")
    args = parser.parse_args(argv)
    r = current_regime(date.fromisoformat(args.date) if args.date else None)
    if r.sahm is None:
        print(f"{r.name} ({r.source})")
    else:
        print(f"{r.name}: {r.source} {r.observed[:7]} = {r.sahm:.2f} (기준 {SAHM_THRESHOLD} 이상이면 {RECESSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
