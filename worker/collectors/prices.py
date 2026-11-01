"""가격·거래량 수집 (C). prices 테이블에 쓴다.

- 국내 전 종목 하루치: pykrx stock.get_market_ohlcv(날짜, market="ALL")  (KRX 로그인 필요: .env 의 KRX_ID·KRX_PW)
  선별 점수(source_select.py)의 "그날 전체 상장 종목 중 순위"에 쓴다. 처음 한 번 252거래일치를 받아 둔다.
- 지수·미국 종목: FinanceDataReader → 실패하면 yfinance.

실행:
  cd worker && python collectors/prices.py today            # 최근 거래일 국내 전 종목 + 지수 4개
  cd worker && python collectors/prices.py backfill 253     # 국내 전 종목 253거래일 (252일 평균 + 당일)
  cd worker && python collectors/prices.py us NVDA 2025-10-01

날짜: market_date 는 그 시장의 거래일이다 (conventions.md). 미국장 10/27 종가는 KST로 10/28 아침에 나오지만 2026-10-27 로 저장한다.
"""
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

import config  # noqa: E402,F401  .env 를 읽어 KRX_ID·KRX_PW 를 환경변수로 올린다
from common.normalize import normalize_kr_code, normalize_us_ticker  # noqa: E402

# 탭1 홈 지수 4개 (서비스흐름 2.1). key = prices.ticker 에 저장하는 값
INDEXES = {
    "KS11": {"fdr": "KS11", "yf": "^KS11", "name": "KOSPI"},
    "KQ11": {"fdr": "KQ11", "yf": "^KQ11", "name": "KOSDAQ"},
    "IXIC": {"fdr": "IXIC", "yf": "^IXIC", "name": "NASDAQ"},
    "US500": {"fdr": "US500", "yf": "^GSPC", "name": "S&P 500"},
}

PRICE_COLUMNS = ["ticker", "market", "market_date", "open", "high", "low", "close", "volume"]

# pykrx get_market_ohlcv(날짜, market="ALL") 의 한글 컬럼
_KR_COLS = {"시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume", "등락률": "chg_pct"}


def ymd(d: date | str) -> str:
    return d.strftime("%Y%m%d") if isinstance(d, date) else d.replace("-", "")


def kr_code(raw: str) -> str:
    """국내 종목 코드. KRX 신규 코드는 영문이 섞인 6자리(예: 우선주 '00104K')라 그대로 둔다.

    common.normalize.normalize_kr_code 가 숫자만 받아서 생긴 임시 처리다. B의 ETF 코드('0015B0')와 같은 문제라
    A에게 영문 허용을 요청했고, 바뀌면 이 함수를 지우고 normalize_kr_code 를 쓴다.
    """
    s = str(raw).strip().upper()
    if len(s) == 6 and s.isalnum() and not s.isdigit():
        return s
    return normalize_kr_code(s)


def kr_daily_from_pykrx(raw: pd.DataFrame, market_date: date) -> pd.DataFrame:
    """pykrx 하루치 표 → PRICE_COLUMNS + chg_pct.

    chg_pct 는 KRX 공식 등락률(전일 기준가 대비, 액면분할·권리락 반영)을 소수로 바꾼 값이다 (0.05 = +5%).
    prices 테이블에는 컬럼이 없어 저장하지 않고 선별 점수에만 쓴다.
    거래량 0(거래정지)인 줄은 뺀다. 거래정지 종목은 그날 주목도 비교 대상이 아니다.
    """
    df = raw.rename(columns=_KR_COLS)[list(_KR_COLS.values())].copy()
    df["ticker"] = [kr_code(c) for c in raw.index.astype(str)]
    df["market"] = "KR"
    df["market_date"] = market_date
    df["chg_pct"] = df["chg_pct"].astype(float) / 100
    df["volume"] = df["volume"].astype("int64")
    df = df[df["volume"] > 0]
    return df[PRICE_COLUMNS + ["chg_pct"]].reset_index(drop=True)


def fetch_kr_daily(d: date, retries: int = 3) -> pd.DataFrame:
    """그날 국내 전 종목(코스피·코스닥·코넥스). 휴장일이면 빈 표.

    KRX 서버가 연속 요청 중에 연결을 끊는 일이 있어(2026-10-28 백필 중 ChunkedEncodingError) 쉬었다가 다시 묻는다.
    """
    from pykrx import stock

    for attempt in range(1, retries + 1):
        try:
            raw = stock.get_market_ohlcv(ymd(d), market="ALL")
            break
        except Exception as e:  # 연결 끊김 등. 마지막 시도면 그대로 올린다
            if attempt == retries:
                raise
            print(f"  {d} 재시도 {attempt}/{retries - 1}: {type(e).__name__}")
            time.sleep(5 * attempt)
    if raw is None or len(raw) == 0:
        return pd.DataFrame(columns=PRICE_COLUMNS + ["chg_pct"])
    return kr_daily_from_pykrx(raw, d)


def kr_trading_days(end: date, n: int) -> list[date]:
    """end 이전(포함) 국내 거래일 n개, 오래된 순. KS11 지수 날짜를 거래일 달력으로 쓴다."""
    import FinanceDataReader as fdr

    start = end - timedelta(days=int(n * 1.6) + 20)  # 주말·공휴일 여유
    idx = fdr.DataReader("KS11", start.isoformat(), end.isoformat()).index
    days = [ts.date() for ts in idx if ts.date() <= end]
    return days[-n:]


def _ohlcv_frame(raw: pd.DataFrame, ticker: str, market: str) -> pd.DataFrame:
    """FDR·yfinance 표(Open/High/Low/Close/Volume, 날짜 인덱스) → PRICE_COLUMNS."""
    if isinstance(raw.columns, pd.MultiIndex):  # yfinance 는 종목 1개여도 (컬럼, 티커) 2단 컬럼일 수 있다
        raw = raw.droplevel(1, axis=1)
    df = pd.DataFrame({
        "ticker": ticker,
        "market": market,
        "market_date": [ts.date() for ts in raw.index],
        "open": raw.get("Open"),
        "high": raw.get("High"),
        "low": raw.get("Low"),
        "close": raw["Close"],
        "volume": raw.get("Volume"),
    }).dropna(subset=["close"])
    df["volume"] = df["volume"].fillna(0).astype("int64")
    return df.reset_index(drop=True)


def _fetch_with_fallback(fdr_symbol: str, yf_symbol: str, ticker: str, market: str,
                         start: date, end: date) -> pd.DataFrame:
    """FinanceDataReader 먼저, 실패하거나 비면 yfinance (기술확정안 데이터 수집 표)."""
    try:
        import FinanceDataReader as fdr

        raw = fdr.DataReader(fdr_symbol, start.isoformat(), end.isoformat())
        if len(raw):
            return _ohlcv_frame(raw, ticker, market)
    except Exception as e:  # 실패 원인은 출력하고 대체 수단으로
        print(f"  FDR 실패 {fdr_symbol}: {type(e).__name__}: {e}")
    import yfinance as yf

    raw = yf.download(yf_symbol, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
                      progress=False, auto_adjust=False)
    return _ohlcv_frame(raw, ticker, market) if len(raw) else pd.DataFrame(columns=PRICE_COLUMNS)


def fetch_index(key: str, start: date, end: date) -> pd.DataFrame:
    info = INDEXES[key]
    return _fetch_with_fallback(info["fdr"], info["yf"], key, "INDEX", start, end)


def fetch_us(ticker: str, start: date, end: date) -> pd.DataFrame:
    t = normalize_us_ticker(ticker)
    return _fetch_with_fallback(t, t, t, "US", start, end)


def save_prices(conn, df: pd.DataFrame) -> int:
    """prices 에 넣는다. 같은 (ticker, market_date)는 새 값으로 덮어쓴다 (수정 종가 반영). 넣은 줄 수를 돌려준다."""
    if df.empty:
        return 0
    rows = [
        (r.ticker, r.market, r.market_date,
         None if pd.isna(r.open) else float(r.open),
         None if pd.isna(r.high) else float(r.high),
         None if pd.isna(r.low) else float(r.low),
         float(r.close), int(r.volume))
        for r in df[PRICE_COLUMNS].itertuples(index=False)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO prices (ticker, market, market_date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, market_date) DO UPDATE SET
                open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                close = EXCLUDED.close, volume = EXCLUDED.volume, collected_at = now()
            """,
            rows,
        )
    return len(rows)


def load_volume_history(conn, tickers: list[str], before: date, n: int = 252) -> pd.DataFrame:
    """종목별 before 직전 거래일 n개의 거래량. 컬럼 ticker, market_date, volume (source_select 가 씀)."""
    rows = conn.execute(
        """
        SELECT ticker, market_date, volume FROM (
            SELECT ticker, market_date, volume,
                   row_number() OVER (PARTITION BY ticker ORDER BY market_date DESC) AS rn
            FROM prices
            WHERE ticker = ANY(%s) AND market_date < %s
        ) t WHERE rn <= %s
        """,
        (tickers, before, n),
    ).fetchall()
    return pd.DataFrame(rows, columns=["ticker", "market_date", "volume"])


def main(argv: list[str]) -> int:
    from db import get_conn

    cmd = argv[0] if argv else "today"
    today = datetime.now().date()
    with get_conn() as conn:
        if cmd == "today":
            d = kr_trading_days(today, 1)[-1]
            n = save_prices(conn, fetch_kr_daily(d))
            print(f"국내 {d}: {n}종목")
            for key in INDEXES:
                n = save_prices(conn, fetch_index(key, today - timedelta(days=10), today))
                print(f"지수 {key}: {n}줄")
        elif cmd == "backfill":
            n_days = int(argv[1]) if len(argv) > 1 else 253
            days = kr_trading_days(today, n_days)
            for i, d in enumerate(days, 1):
                n = save_prices(conn, fetch_kr_daily(d))
                conn.commit()  # 중간에 끊겨도 받은 날은 남긴다
                print(f"[{i}/{len(days)}] {d}: {n}종목")
                time.sleep(1)  # KRX 서버 부담을 줄인다
            for key in INDEXES:
                n = save_prices(conn, fetch_index(key, days[0] - timedelta(days=400), today))
                print(f"지수 {key}: {n}줄")
        elif cmd == "us":
            ticker, start = argv[1], date.fromisoformat(argv[2])
            print(f"{ticker}: {save_prices(conn, fetch_us(ticker, start, today))}줄")
        else:
            print(__doc__)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
