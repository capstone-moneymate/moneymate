"""1차 자료 선별 (C). 기술확정안 "1차 자료 선별" 표를 그대로 코드로 옮긴다.

1. 거르기 (점수 없음): passes_filter_dart / passes_filter_8k
2. 점수 0~4: 비정상 거래량 0~2 + 극단적 수익률 0~2 (Barber & Odean 2008, 3.1~3.2절)
   - 국내 종목: 그날 전체 상장 종목 중 순위 (cross_section_scores)
   - 지수·미국 종목: 자기 과거 252거래일 중 순위 (own_history_score, "변형")
   - 반응일: 장중 발표는 당일, 장 마감 후 발표는 다음 거래일 (reaction_day)
3. 고르기 최대 3건: 같은 회사·사건 1건, 시작 개념 없으면 넘김, 유형 3 1건 우선, 테마·유형 섞기 (select)

이 파일은 DB·네트워크를 쓰지 않는 순수 함수만 둔다. 손계산 예시는 tests/test_source_select.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd

KST = ZoneInfo("Asia/Seoul")
ET = ZoneInfo("America/New_York")
MARKET_CLOSE = {"KR": (KST, time(15, 30)), "US": (ET, time(16, 0))}

LOOKBACK = 252  # 비정상 거래량 = 그날 ÷ 직전 252거래일 평균 (식 (1)(2))

# ------------------------------------------------------------------
# 1. 거르기
# ------------------------------------------------------------------
# DART 보고서명(report_nm)에 들어 있으면 포함. 기술확정안 0~1단계
DART_INCLUDE = {
    "단일판매ㆍ공급계약체결": "supply_contract",
    "단일판매·공급계약체결": "supply_contract",
    "영업(잠정)실적": "earnings",
    "매출액또는손익구조": "earnings",
    "자기주식취득결정": "buyback",
    "주식소각결정": "buyback",
    "신규시설투자": "capex",
}
# 들어 있으면 제외: 정정 공시, 반복성 공시, 의무 기준 미만(자율공시)
DART_EXCLUDE = (
    "정정",  # [기재정정] [첨부정정] 등
    "임원ㆍ주요주주",
    "주식등의대량보유",
    "자율공시",  # 공급계약 의무 기준(매출액 5%·2.5%·10%) 미만은 자율공시로 낸다
)
# 8-K Item 2.02(실적), 1.01(중요 계약)
SEC_8K_ITEMS = {"2.02": "earnings", "1.01": "material_agreement"}


def dart_category(report_nm: str) -> str | None:
    """포함 대상이면 종류(supply_contract 등), 아니면 None."""
    name = re.sub(r"\s+", "", report_nm)
    if any(x in name for x in DART_EXCLUDE):
        return None
    for key, cat in DART_INCLUDE.items():
        if key in name:
            return cat
    return None


def sec_8k_category(items: list[str] | str) -> str | None:
    """8-K 항목 목록(예: ['2.02', '9.01'])에서 포함 대상 종류. 2.02가 먼저."""
    found = re.findall(r"\d\.\d\d", items if isinstance(items, str) else " ".join(items))
    for item, cat in SEC_8K_ITEMS.items():
        if item in found:
            return cat
    return None


# ------------------------------------------------------------------
# 2. 반응일과 점수
# ------------------------------------------------------------------
def reaction_day(published_at: datetime, market: str, trading_days: list[date]) -> date | None:
    """장중(마감 전) 발표는 당일, 마감 후·휴장일 발표는 다음 거래일. 달력 안에 없으면 None.

    published_at 은 timezone-aware 여야 한다. market 의 현지 시각으로 바꿔 마감 시각과 비교한다.
    trading_days 는 그 시장의 거래일 목록(오름차순).
    """
    if published_at.tzinfo is None:
        raise ValueError("published_at 은 timezone-aware 여야 한다 (conventions.md P10)")
    tz, close = MARKET_CLOSE[market]
    local = published_at.astimezone(tz)
    d, t = local.date(), local.time()
    for td in trading_days:
        if td == d and t < close:
            return td
        if td > d:
            return td
    return None


def reaction_window_date_only(d: date, trading_days: list[date]) -> list[date]:
    """발표 시각을 모르는 자료(DART 는 접수일만 준다)의 반응일 후보: 당일(거래일이면)과 다음 거래일.

    MacKinlay(1997) "사건 기간에 최소한 발표 당일과 다음 날을 포함"을 따른 것이다.
    두 날의 점수 중 큰 값을 쓴다 (호출하는 쪽). 다음 거래일 데이터가 있어야 하므로 카드는 하루 늦다. 팀 확인 필요.
    """
    same = [td for td in trading_days if td == d]
    after = [td for td in trading_days if td > d][:1]
    return same + after


def quantile_score(q: float) -> int:
    """위쪽 순위 비율 q(0~1, 1이 가장 큼)를 점수로: 상위 5% → 2, 상위 10% → 1."""
    if q > 0.95:
        return 2
    if q > 0.90:
        return 1
    return 0


def two_tail_score(q: float) -> int:
    """수익률은 양쪽 끝: 위·아래 5% → 2, 10% → 1.

    20종목 예: q = 순위/20. 가장 큰 1개(q=1.0)와 가장 작은 1개(q=0.05)가 2점, 그다음 각 1개가 1점.
    """
    if q > 0.95 or q <= 0.05:
        return 2
    if q > 0.90 or q <= 0.10:
        return 1
    return 0


def cross_section_scores(day: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """국내 전 종목의 그날 점수.

    day: ticker, volume, chg_pct (그날 전 종목, prices.fetch_kr_daily)
    history: ticker, market_date, volume (종목별 직전 거래일들, prices.load_volume_history)
    직전 252거래일이 다 차지 않은 종목(신규 상장 등)은 순위에서 빼고 0점.
    돌려주는 표: ticker, abn_volume, vol_q, ret_q, vol_score, ret_score, score
    """
    g = history.groupby("ticker")["volume"]
    stats = pd.DataFrame({"avg": g.mean(), "n": g.size()})
    df = day[["ticker", "volume", "chg_pct"]].merge(stats, left_on="ticker", right_index=True, how="left")
    ok = (df["n"] >= LOOKBACK) & (df["avg"] > 0)
    df["abn_volume"] = (df["volume"] / df["avg"]).where(ok)
    ranked = df[ok]
    # 순위 비율: 오름차순 순위 ÷ 종목 수. 20종목이면 1등(가장 큼) q=1.0, 2등 q=0.95
    df["vol_q"] = ranked["abn_volume"].rank(method="average") / len(ranked)
    df["ret_q"] = ranked["chg_pct"].rank(method="average") / len(ranked)
    df["vol_score"] = df["vol_q"].map(lambda q: 0 if pd.isna(q) else quantile_score(q))
    df["ret_score"] = df["ret_q"].map(lambda q: 0 if pd.isna(q) else two_tail_score(q))
    df["score"] = df["vol_score"] + df["ret_score"]
    return df[["ticker", "abn_volume", "vol_q", "ret_q", "vol_score", "ret_score", "score"]]


def own_history_q(value: float, history: list[float]) -> float:
    """value 가 (과거 + 그날) 중 몇 번째로 큰지의 비율. 과거 252개 + 그날 = 253개 중 가장 크면 1.0.

    동률은 평균 순위 (pandas rank method='average' 와 같다).
    """
    values = list(history) + [value]
    below = sum(1 for v in values if v < value)
    same = sum(1 for v in values if v == value)
    return (below + (same + 1) / 2) / len(values)


def own_history_score(volumes: list[float], returns: list[float]) -> dict:
    """지수·미국 종목 (변형: 전 종목 비교 대신 자기 과거 252거래일과 비교). 마지막 값이 반응일.

    volumes: 과거 252 + 반응일 1. 반응일 거래량이 과거 252일 거래량 중 몇 번째인지 본다
             (날마다 비정상 거래량을 다시 만들려면 504일치가 필요해서 단순화. 팀 확인 필요).
             거래량이 없으면(0·NaN) 0점.
    returns: 과거 252 + 반응일 1 일간 수익률.
    과거가 252개보다 적으면 그 항목은 0점.
    """
    vol_score = 0
    if len(volumes) > LOOKBACK and volumes[-1] and volumes[-1] == volumes[-1]:
        vol_score = quantile_score(own_history_q(volumes[-1], volumes[-LOOKBACK - 1:-1]))
    ret_score = 0
    if len(returns) > LOOKBACK:
        ret_score = two_tail_score(own_history_q(returns[-1], returns[-LOOKBACK - 1:-1]))
    return {"vol_score": vol_score, "ret_score": ret_score, "score": vol_score + ret_score}


# ------------------------------------------------------------------
# 3. 고르기
# ------------------------------------------------------------------
@dataclass
class Candidate:
    source_id: str              # raw_sources 의 원 출처 id (DART rcept_no, 8-K accession 등)
    event_key: str              # 같은 회사·사건 판정용 (회사 코드, 거시 발표 id)
    published_at: datetime
    vol_score: int = 0
    ret_score: int = 0
    theme: str | None = None    # 금리 / AI·반도체 / ... (업종 분류·KRX 섹터 지수로 붙임)
    card_type: int | None = None  # 1·2·3. classify 결과 (3주차). 모르면 None
    start_concept: str | None = None
    is_price_card: bool = False  # 1차 자료가 아닌 가격 데이터 카드 (모자랄 때 채우기용)
    extra: dict = field(default_factory=dict)

    @property
    def score(self) -> int:
        return self.vol_score + self.ret_score


def rank_key(c: Candidate):
    """동점은 거래량 → 수익률 → 최신순 (Barber & Odean 4절: 거래량이 가장 좋은 주목 지표)."""
    return (-c.score, -c.vol_score, -c.ret_score, -c.published_at.timestamp())


def select(candidates: list[Candidate], max_n: int = 3) -> list[Candidate]:
    """점수 1점 이상 후보에서 최대 max_n 건.

    순서: (1) 유형 3이 있으면 가장 높은 1건 먼저 → (2) 아직 안 나온 테마·유형 우선 → (3) 남은 자리는 순위대로
          → (4) 그래도 모자라면 가격 데이터 카드(유형 1). 같은 event_key 는 1건만, start_concept 없으면 넘긴다.
    """
    pool = sorted((c for c in candidates if c.score >= 1 and c.start_concept and not c.is_price_card),
                  key=rank_key)
    picked: list[Candidate] = []
    used_events: set[str] = set()

    def take(c: Candidate) -> None:
        picked.append(c)
        used_events.add(c.event_key)

    def available(c: Candidate) -> bool:
        return c.event_key not in used_events and c not in picked

    for c in pool:  # (1)
        if c.card_type == 3:
            take(c)
            break
    for c in pool:  # (2)
        if len(picked) >= max_n:
            break
        if available(c) and c.theme not in {p.theme for p in picked} \
                and c.card_type not in {p.card_type for p in picked}:
            take(c)
    for c in pool:  # (3)
        if len(picked) >= max_n:
            break
        if available(c):
            take(c)
    price = sorted((c for c in candidates if c.is_price_card and c.score >= 1), key=rank_key)
    for c in price:  # (4)
        if len(picked) >= max_n:
            break
        if available(c):
            take(c)
    return picked
