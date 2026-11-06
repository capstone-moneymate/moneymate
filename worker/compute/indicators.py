"""지표 계산 (B). RSI·기간 수익률·거래량 배수·거래량 상위일. DB 를 부르지 않는 순수 함수만 둔다.

출제 도구(generate/tools.py)와 차트 읽기 화면이 같은 함수를 써서 정답과 화면 숫자가 어긋나지 않게 한다.
계산 방식은 C의 tools.py(agent-tools-42)에 있던 것을 그대로 옮겼다. C와 합의: 계산은 여기, tools.py 는 가져다 쓴다.

RSI 는 Wilder(1978) 원래 정의다: 첫 평균은 처음 period 개 변화의 단순 평균, 그다음은
평균 = (이전 평균 × (period-1) + 오늘 값) ÷ period. 기술확정안의 pandas-ta-classic rsi() 는 같은 평활을 ewm 으로
근사해 시작값만 다르다. 252거래일을 넣으면 소수 2자리까지 같고, 60거래일보다 짧으면 차이가 난다 (docs/modules/indicators.md).

입력이 부족하면 ValueError 를 올린다. tools.py 는 이를 ToolError 로 바꿔 에이전트에게 보여 준다.
"""
import pandas as pd


def _rsi(gain: float, loss: float) -> float:
    if loss == 0:
        return 100.0
    return round(100 - 100 / (1 + gain / loss), 2)


def rsi_series(closes: list[float], period: int = 14) -> list[float | None]:
    """날짜마다의 RSI (closes 와 같은 길이). 앞의 period 개는 계산할 변화가 모자라 None. 차트에 선으로 그릴 때 쓴다.

    i 번째 값은 wilder_rsi(closes[:i+1], period) 와 같다.
    """
    if period < 1:
        raise ValueError(f"RSI 기간은 1 이상이어야 해요: {period}")
    out: list[float | None] = [None] * len(closes)
    if len(closes) < period + 1:
        return out
    diffs = [b - a for a, b in zip(closes, closes[1:])]
    gain = sum(max(d, 0) for d in diffs[:period]) / period
    loss = sum(max(-d, 0) for d in diffs[:period]) / period
    out[period] = _rsi(gain, loss)
    for i, d in enumerate(diffs[period:], start=period + 1):
        gain = (gain * (period - 1) + max(d, 0)) / period
        loss = (loss * (period - 1) + max(-d, 0)) / period
        out[i] = _rsi(gain, loss)
    return out


def wilder_rsi(closes: list[float], period: int = 14) -> float:
    """마지막 날 RSI. 손실이 0이면 100. 소수 2자리."""
    if len(closes) < period + 1:
        raise ValueError(f"RSI {period}일을 계산하려면 종가가 {period + 1}개 이상 필요해요 (지금 {len(closes)}개)")
    return rsi_series(closes, period)[-1]


def pct_return(start_close: float, end_close: float) -> float:
    """기간 수익률(%). 소수 2자리. 200 → 210 = 5.0"""
    return round((end_close / start_close - 1) * 100, 2)


def volume_ratio(volumes: list[float]) -> float:
    """마지막 날 거래량 ÷ 그 앞 날들 평균. 소수 2자리. 비정상 거래량(Barber & Odean 2008)은 앞 252일을 넣는다."""
    *before, today = volumes
    if not before:
        raise ValueError("평균을 낼 이전 거래일이 없어요")
    avg = sum(before) / len(before)
    return round(today / avg, 2) if avg else 0.0


def top_volume_days(df: pd.DataFrame, n: int) -> list[dict]:
    """market_date·volume 컬럼 표에서 거래량 큰 순 n 일. 같으면 이른 날 먼저."""
    top = df.sort_values(["volume", "market_date"], ascending=[False, True]).head(n)
    return [{"date": str(r.market_date), "volume": int(r.volume)} for r in top.itertuples()]
