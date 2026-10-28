"""source_select.py 손계산 예시. 숫자는 손으로 계산한 값이 정답이다."""
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from compute.source_select import (
    LOOKBACK,
    Candidate,
    cross_section_scores,
    dart_category,
    own_history_score,
    reaction_day,
    reaction_window_date_only,
    sec_8k_category,
    select,
    two_tail_score,
)
from compute.source_select import KST, ET

# ---------------- 1. 거르기 ----------------


@pytest.mark.parametrize("name, expected", [
    ("단일판매ㆍ공급계약체결", "supply_contract"),
    ("영업(잠정)실적(공정공시)", "earnings"),
    ("주요사항보고서(자기주식취득결정)", "buyback"),
    ("주식소각결정", "buyback"),
    ("신규시설투자등", "capex"),
    ("[기재정정]단일판매ㆍ공급계약체결", None),         # 정정 공시 제외
    ("단일판매ㆍ공급계약체결(자율공시)", None),          # 의무 기준 미만 제외
    ("임원ㆍ주요주주특정증권등소유상황보고서", None),    # 반복성 공시 제외
    ("주식등의대량보유상황보고서(일반)", None),
    ("투자설명서", None),                               # 포함 목록에 없음
])
def test_dart_category(name, expected):
    assert dart_category(name) == expected


def test_sec_8k_category():
    assert sec_8k_category(["2.02", "9.01"]) == "earnings"
    assert sec_8k_category("Item 1.01, Item 9.01") == "material_agreement"
    assert sec_8k_category(["5.02"]) is None


# ---------------- 2. 반응일 ----------------

KR_DAYS = [date(2026, 10, 23), date(2026, 10, 26), date(2026, 10, 27)]  # 금, 월, 화


def test_reaction_day_kr_intraday_same_day():
    # 10/26(월) 10:00 KST 발표 → 당일
    assert reaction_day(datetime(2026, 10, 26, 10, 0, tzinfo=KST), "KR", KR_DAYS) == date(2026, 10, 26)


def test_reaction_day_kr_after_close_next_day():
    # 15:30 정각은 마감 후로 본다 → 다음 거래일
    assert reaction_day(datetime(2026, 10, 26, 15, 30, tzinfo=KST), "KR", KR_DAYS) == date(2026, 10, 27)


def test_reaction_day_kr_weekend_next_monday():
    # 10/24(토) → 10/26(월)
    assert reaction_day(datetime(2026, 10, 24, 9, 0, tzinfo=KST), "KR", KR_DAYS) == date(2026, 10, 26)


def test_reaction_day_us_uses_new_york_time():
    us_days = [date(2026, 10, 26), date(2026, 10, 27)]
    # 10/27 04:00 KST = 10/26 15:00 EDT (장중) → 미국 10/26
    t = datetime(2026, 10, 26, 19, 0, tzinfo=timezone.utc)
    assert t.astimezone(ET).hour == 15
    assert reaction_day(t, "US", us_days) == date(2026, 10, 26)
    # 10/26 16:05 EDT (장 마감 후 실적) → 10/27
    assert reaction_day(datetime(2026, 10, 26, 16, 5, tzinfo=ET), "US", us_days) == date(2026, 10, 27)


def test_reaction_window_date_only():
    # DART 10/26(월) 접수, 시각 모름 → 10/26, 10/27 둘 다 본다. 토요일 접수 → 월요일만
    assert reaction_window_date_only(date(2026, 10, 26), KR_DAYS) == [date(2026, 10, 26), date(2026, 10, 27)]
    assert reaction_window_date_only(date(2026, 10, 24), KR_DAYS) == [date(2026, 10, 26)]


def test_reaction_day_requires_timezone():
    with pytest.raises(ValueError):
        reaction_day(datetime(2026, 10, 26, 10, 0), "KR", KR_DAYS)


# ---------------- 3. 점수 ----------------


def test_two_tail_score_20_stocks():
    # 20종목: q = 순위/20. 위 2개, 아래 2개만 점수
    scores = [two_tail_score(r / 20) for r in range(1, 21)]
    assert scores == [2, 1] + [0] * 16 + [1, 2]


def _history(tickers, avg):
    """종목마다 252일 동안 거래량이 avg 로 같은 과거."""
    return pd.DataFrame([
        {"ticker": t, "market_date": date(2025, 1, 1) + timedelta(days=i), "volume": avg}
        for t in tickers for i in range(LOOKBACK)
    ])


def test_cross_section_scores_hand_example():
    # 20종목, 평균 거래량 모두 1,000. 그날 거래량 = 1,000 × k (k=1..20) → 비정상 거래량 = k
    # 수익률은 거래량과 반대 순서: 종목 k 의 수익률 = (10 - k) / 100
    tickers = [f"{k:06d}" for k in range(1, 21)]
    day = pd.DataFrame({
        "ticker": tickers,
        "volume": [1000 * k for k in range(1, 21)],
        "chg_pct": [(10 - k) / 100 for k in range(1, 21)],
    })
    out = cross_section_scores(day, _history(tickers, 1000)).set_index("ticker")
    # 종목 20: 거래량 1등(상위 5%) 2점 + 수익률 꼴찌(하위 5%) 2점 = 4점
    assert out.loc["000020", "abn_volume"] == 20
    assert (out.loc["000020", "vol_score"], out.loc["000020", "ret_score"]) == (2, 2)
    # 종목 19: 거래량 2등 1점 + 수익률 뒤에서 2등 1점 = 2점
    assert out.loc["000019", "score"] == 2
    # 종목 1: 거래량 꼴찌 0점 + 수익률 1등(+9%) 2점 = 2점
    assert (out.loc["000001", "vol_score"], out.loc["000001", "ret_score"]) == (0, 2)
    # 종목 10: 가운데 → 0점
    assert out.loc["000010", "score"] == 0


def test_cross_section_excludes_short_history():
    # 신규 상장(과거 10일뿐)은 순위에서 빠지고 0점, 나머지 종목 수로만 순위를 낸다
    tickers = [f"{k:06d}" for k in range(1, 21)]
    hist = pd.concat([_history(tickers, 1000), pd.DataFrame(
        [{"ticker": "999999", "market_date": date(2026, 1, 1), "volume": 1} for _ in range(10)])])
    day = pd.DataFrame({
        "ticker": tickers + ["999999"],
        "volume": [1000 * k for k in range(1, 21)] + [10**9],
        "chg_pct": [0.0] * 20 + [0.3],
    })
    out = cross_section_scores(day, hist).set_index("ticker")
    assert out.loc["999999", "score"] == 0
    assert pd.isna(out.loc["999999", "abn_volume"])
    assert out.loc["000020", "vol_score"] == 2


def test_own_history_score_index():
    # 과거 252일 거래량 1..252, 반응일 300 → 253개 중 1등(q=1.0) → 2점
    # 과거 수익률 -0.126..+0.125 (0.001 간격), 반응일 -0.05 → 가운데쯤 → 0점
    vols = list(range(1, LOOKBACK + 1)) + [300]
    rets = [(i - 126) / 1000 for i in range(LOOKBACK)] + [-0.05]
    assert own_history_score(vols, rets) == {"vol_score": 2, "ret_score": 0, "score": 2}


def test_own_history_score_index_without_volume():
    # 지수 거래량이 없으면 거래량 점수 0, 수익률만. 반응일 -0.2 는 과거보다 가장 낮음 → 2점
    rets = [(i - 126) / 1000 for i in range(LOOKBACK)] + [-0.2]
    assert own_history_score([0] * (LOOKBACK + 1), rets)["score"] == 2


def test_own_history_score_short_history_is_zero():
    assert own_history_score([1, 2, 3], [0.1, 0.2, 0.5])["score"] == 0


# ---------------- 4. 고르기 ----------------

T0 = datetime(2026, 10, 27, 7, 0, tzinfo=timezone.utc)


def c(sid, score_v, score_r, theme="AI·반도체", card_type=1, concept="semi_earnings",
      event=None, minutes=0, price=False):
    return Candidate(source_id=sid, event_key=event or sid, published_at=T0 + timedelta(minutes=minutes),
                     vol_score=score_v, ret_score=score_r, theme=theme, card_type=card_type,
                     start_concept=concept, is_price_card=price)


def ids(picked):
    return [p.source_id for p in picked]


def test_select_tie_break_volume_then_return_then_latest():
    # 모두 2점: b(거래량 2) > a(거래량 1, 최신) = d(거래량 1) ... a 가 d 보다 최신
    a = c("a", 1, 1, minutes=10, event="a")
    b = c("b", 2, 0, event="b")
    d = c("d", 1, 1, minutes=0, event="d")
    assert ids(select([a, b, d], max_n=3)) == ["b", "a", "d"]


def test_select_drops_zero_score_and_missing_concept():
    assert select([c("a", 0, 0), c("b", 2, 2, concept=None)]) == []


def test_select_same_event_once():
    # 같은 회사 공시 2건이면 점수 높은 1건만
    picked = select([c("a1", 2, 2, event="005930"), c("a2", 2, 1, event="005930"), c("b", 1, 0)])
    assert ids(picked) == ["a1", "b"]


def test_select_type3_first_then_mix_theme_and_type():
    x = c("x", 2, 2, theme="AI·반도체", card_type=1)
    y = c("y", 2, 1, theme="AI·반도체", card_type=1)
    z = c("z", 1, 0, theme="금리", card_type=2)
    t3 = c("t3", 1, 0, theme="AI·반도체", card_type=3)
    # 유형 3 먼저(t3) → 테마·유형이 둘 다 새로운 것: x 는 테마가 같아 넘기고 z(금리, 유형2) → 남은 자리 x
    assert ids(select([x, y, z, t3])) == ["t3", "z", "x"]


def test_select_fills_with_price_cards():
    real = c("a", 2, 0)
    p1 = c("kospi", 0, 2, theme="차트 읽기", concept="consecutive_rise", price=True)
    p0 = c("kosdaq", 0, 0, theme="차트 읽기", concept="consecutive_rise", price=True)
    # 1차 자료 1건 + 가격 카드 1건. 0점 가격 카드는 안 넣음 → 그날은 2건만
    assert ids(select([real, p1, p0])) == ["a", "kospi"]
