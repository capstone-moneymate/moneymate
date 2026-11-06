"""액티브 ETF 구성종목 일일 수집 (B). holdings_etf 테이블에 쓴다.

- pykrx stock.get_etf_portfolio_deposit_file(code, 날짜)  (KRX 로그인 필요: .env 의 KRX_ID·KRX_PW)
- 수량은 ETF 전체 보유량이 아니라 1CU(설정 단위)당 수량이다. 그래서 자금 유입 보정은 하지 않는다 (findings.md B칸).

실행:
  cd worker && python collectors/etf_holdings.py today                  # 최근 거래일 스냅샷 저장
  cd worker && python collectors/etf_holdings.py backfill 2026-09-30    # 그날부터 최근 거래일까지 빠진 날 저장
  cd worker && python collectors/etf_holdings.py show 2026-10-30        # 저장하지 않고 정제 결과만 출력

규칙 (docs/conventions.md)
- P6: 한 번 받은 날짜는 덮어쓰지 않는다 (ON CONFLICT DO NOTHING). source 컬럼에 출처를 남긴다
- P16: 구성종목 코드(CUSIP 2~7번째 글자)는 raw_code 에 그대로, ticker 는 cusip_map 으로 맞춰 채운다(못 찾으면 NULL).
       6자리가 다른 회사와 겹칠 수 있어 종목명도 비교해, 다르면 채우지 않고 출력한다.
       주식만 저장하고 원화현금 010010, 설정현금액 H00000, 선물은 뺀다.
       설정 단위가 바뀌면 전 종목 수량이 같은 비율로 변하므로 경고한다
"""
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

import config  # noqa: E402,F401  .env 를 읽어 KRX_ID·KRX_PW 를 환경변수로 올린다
from common.normalize import normalize_kr_code  # noqa: E402

KST = ZoneInfo("Asia/Seoul")  # 배포 서버(UTC)에서도 한국 날짜로 돌도록

# 수집 대상 (분담표 B-1). KoAct 코드는 2026-10-11 pykrx ETF 목록에서 확인
ETFS = {
    "426030": "TIME 미국나스닥100액티브",
    "0015B0": "KoAct 미국나스닥성장기업액티브",
}
NON_STOCK_CODES = {"010010", "H00000"}  # 원화현금, 설정현금액
HOLDING_COLUMNS = ["etf_code", "snapshot_date", "raw_code", "stock_name", "shares"]

# 설정 단위 변경 경고: 겹치는 종목이 이만큼 이상이고, 모든 종목의 수량 비율이 같으면 경고
UNIT_CHANGE_MIN_COMMON = 5
UNIT_CHANGE_TOLERANCE = 0.005  # 비율 차이 0.5% 안이면 "같은 비율"로 본다 (소수 수량 반올림 여유)

# 종목명 비교에서 빼는 단어: 회사 형태·주식 종류처럼 다른 회사도 흔히 같이 쓰는 말
GENERIC_NAME_WORDS = {
    "INC", "CORP", "CORPORATION", "CO", "COM", "COMPANY", "LTD", "LIMITED", "PLC", "NV", "SA", "AG", "DE", "THE", "NEW",
    "CL", "CLASS", "SP", "ADR", "HOLDING", "HOLDINGS", "GROUP", "GLOBAL", "INTERNATIONAL", "INTL",
    "TECH", "TECHNOLOGY", "TECHNOLOGIES", "SYSTEMS",
}


def is_non_stock(code: str, name: str) -> bool:
    """현금·선물처럼 주식이 아닌 줄. 주식 코드는 6자리라 그 외 길이는 선물로 본다 (예: NQZ6)."""
    return code in NON_STOCK_CODES or "현금" in name or len(code) != 6


def holdings_from_pykrx(raw: pd.DataFrame, etf_code: str, snapshot_date: date) -> pd.DataFrame:
    """pykrx 구성종목 표(index=코드, 컬럼 구성종목명·계약수 …) → HOLDING_COLUMNS. 주식 줄만 남긴다.

    수량은 Decimal 로 바꾼다. KoAct 처럼 소수(99.88)가 오는데 float 로 넣으면 NUMERIC 에 오차가 섞인다.
    같은 코드가 두 줄이면 합친다. 수량 0 이하는 보유가 아니라서 뺀다.
    """
    codes = raw.index.astype(str).str.strip().str.upper()
    names = raw["구성종목명"].astype(str).str.strip()
    keep = [not is_non_stock(c, n) for c, n in zip(codes, names)]
    df = pd.DataFrame({
        "raw_code": codes[keep],
        "stock_name": names[keep].to_numpy(),
        "shares": [Decimal(str(v)) for v in raw["계약수"].to_numpy()[keep]],
    })
    df = df[df["shares"] > 0]
    df = (df.groupby("raw_code", as_index=False, sort=False)
            .agg(stock_name=("stock_name", "first"), shares=("shares", "sum")))
    df.insert(0, "etf_code", normalize_kr_code(etf_code))
    df.insert(1, "snapshot_date", snapshot_date)
    return df[HOLDING_COLUMNS].reset_index(drop=True)


def unit_change_ratio(prev: dict[str, Decimal], curr: dict[str, Decimal]) -> float | None:
    """두 스냅샷에 모두 있는 종목의 수량이 전부 같은 비율로 변했으면 그 비율, 아니면 None.

    1CU 수량은 운용사가 사고팔면 종목마다 다르게 변한다. 전 종목이 같은 비율(예: 2배)로 변했다면
    매매가 아니라 설정 단위를 바꾼 것이라, 그대로 두면 추세가 전부 "늘림"으로 잘못 나온다.
    """
    common = [k for k in curr if k in prev and prev[k] > 0]
    if len(common) < UNIT_CHANGE_MIN_COMMON:
        return None
    ratios = [float(curr[k] / prev[k]) for k in common]
    mid = sorted(ratios)[len(ratios) // 2]
    if abs(mid - 1) <= UNIT_CHANGE_TOLERANCE:
        return None
    if all(abs(r / mid - 1) <= UNIT_CHANGE_TOLERANCE for r in ratios):
        return mid
    return None


def fetch_holdings(etf_code: str, d: date, retries: int = 3) -> pd.DataFrame:
    """그날 구성종목. 로그인 실패나 휴장일이면 빈 표.

    KRX 서버가 연속 요청 중에 연결을 끊는 일이 있어(prices.py 와 같은 문제) 쉬었다가 다시 묻는다.
    """
    from pykrx import stock

    for attempt in range(1, retries + 1):
        try:
            raw = stock.get_etf_portfolio_deposit_file(etf_code, d.strftime("%Y%m%d"))
            break
        except Exception as e:  # 연결 끊김 등. 마지막 시도면 그대로 올린다
            if attempt == retries:
                raise
            print(f"  {etf_code} {d} 재시도 {attempt}/{retries - 1}: {type(e).__name__}")
            time.sleep(5 * attempt)
    if raw is None or len(raw) == 0:
        return pd.DataFrame(columns=HOLDING_COLUMNS)
    return holdings_from_pykrx(raw, etf_code, d)


def latest_trading_day(today: date) -> date:
    """today 이전(포함) 가장 최근 거래일. trading_days_since 와 같은 달력을 써서 둘이 어긋나지 않게 한다."""
    from collectors.prices import kr_trading_days

    return kr_trading_days(today, 1)[-1]


def trading_days_since(start: date, end: date) -> list[date]:
    """start~end 국내 거래일, 오래된 순. 거래일 달력은 C의 prices.kr_trading_days(KS11 지수 날짜)를 쓴다."""
    from collectors.prices import kr_trading_days

    n = (end - start).days + 1
    return [d for d in kr_trading_days(end, n) if d >= start]


def saved_dates(conn, etf_code: str) -> set[date]:
    rows = conn.execute("SELECT DISTINCT snapshot_date FROM holdings_etf WHERE etf_code = %s", (etf_code,)).fetchall()
    return {d for (d,) in rows}


def previous_snapshot(conn, etf_code: str, before: date) -> tuple[date | None, dict[str, Decimal]]:
    """before 직전 스냅샷 (날짜, {raw_code: shares}). 없으면 (None, {})."""
    (prev_date,) = conn.execute(
        "SELECT max(snapshot_date) FROM holdings_etf WHERE etf_code = %s AND snapshot_date < %s",
        (etf_code, before),
    ).fetchone()
    if prev_date is None:
        return None, {}
    rows = conn.execute(
        "SELECT raw_code, shares FROM holdings_etf WHERE etf_code = %s AND snapshot_date = %s",
        (etf_code, prev_date),
    ).fetchall()
    return prev_date, dict(rows)


def save_holdings(conn, df: pd.DataFrame, source: str = "pykrx") -> int:
    """holdings_etf 에 넣는다. 이미 있는 (etf_code, snapshot_date, raw_code)는 건드리지 않는다 (P6). 새로 넣은 줄 수를 돌려준다."""
    inserted = 0
    with conn.cursor() as cur:
        for r in df[HOLDING_COLUMNS].itertuples(index=False):
            cur.execute(
                """
                INSERT INTO holdings_etf (etf_code, snapshot_date, raw_code, stock_name, shares, source)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (etf_code, snapshot_date, raw_code) DO NOTHING
                """,
                (r.etf_code, r.snapshot_date, r.raw_code, r.stock_name, r.shares, source),
            )
            inserted += cur.rowcount
    return inserted


def name_words(name: str | None) -> set[str]:
    """종목명 → 비교할 단어들. 대문자로 바꾸고 문장부호로 나눈 뒤 흔한 말과 한 글자(주식 종류 A 등)는 뺀다."""
    words = re.findall(r"[A-Z0-9]+", (name or "").upper())
    return {w for w in words if len(w) > 1 and w not in GENERIC_NAME_WORDS}


def same_company(stock_name: str | None, issuer_name: str | None) -> bool:
    """ETF 종목명과 13F 발행사명이 같은 회사로 보이는가. 단어가 하나라도 겹치면 같다고 본다.

    표기가 제각각이라(TESLA MOTORS / TESLA INC, TEXAS INSTRUMENTS / TEXAS INSTRS) 완전히 같은지는 보지 않는다.
    겹치는 말이 없으면 다른 회사로 보고, 채운 결과는 출력해서 사람이 확인한다.
    """
    return bool(name_words(stock_name) & name_words(issuer_name))


def fill_tickers(conn) -> int:
    """ticker 가 빈 줄을 cusip_map 으로 채운다 (P16). raw_code = CUSIP 2~7번째 글자.

    맨 앞 글자가 빠져 있어 6자리가 다른 회사와 겹칠 수 있다. 한 raw_code 에 티커가 둘 이상 나오면 채우지 않는다.
    ETF 에만 있는 종목이 13F 의 다른 회사와 겹치는 경우는 위 조건으로 못 막아서, 종목명까지 비교해 다르면 채우지 않는다.
    cusip_map 은 A의 13F 수집이 채우므로 13F 에 없는 종목은 NULL 로 남는다. 채운 줄 수를 돌려준다.
    """
    candidates = conn.execute(
        """
        SELECT DISTINCT h.raw_code, h.stock_name, m.ticker, m.issuer_name
        FROM holdings_etf h
        JOIN (
            SELECT substr(cusip, 2, 6) AS raw_code, min(ticker) AS ticker, min(issuer_name) AS issuer_name
            FROM cusip_map WHERE ticker IS NOT NULL
            GROUP BY substr(cusip, 2, 6)
            HAVING count(DISTINCT ticker) = 1
        ) m ON h.raw_code = m.raw_code
        WHERE h.ticker IS NULL
        ORDER BY h.raw_code, h.stock_name
        """
    ).fetchall()
    filled = 0
    for raw_code, stock_name, ticker, issuer_name in candidates:
        if not same_company(stock_name, issuer_name):
            print(f"  ⚠ ticker 안 채움 (종목명 다름): {raw_code} {stock_name} ≠ {ticker} {issuer_name}")
            continue
        print(f"  ticker 채움: {raw_code} {stock_name} → {ticker} {issuer_name}")
        filled += conn.execute(
            "UPDATE holdings_etf SET ticker = %s WHERE ticker IS NULL AND raw_code = %s AND stock_name = %s",
            (ticker, raw_code, stock_name),
        ).rowcount
    return filled


def collect_day(conn, etf_code: str, d: date) -> int:
    """하루치를 받아 저장하고, 직전 스냅샷과 비교해 설정 단위 변경을 경고한다."""
    df = fetch_holdings(etf_code, d)
    if df.empty:
        print(f"  {etf_code} {d}: 결과 없음 (로그인 실패이거나 그날 데이터 없음)")
        return 0
    prev_date, prev = previous_snapshot(conn, etf_code, d)
    ratio = unit_change_ratio(prev, dict(zip(df["raw_code"], df["shares"])))
    if ratio is not None:
        print(f"  ⚠ {etf_code} {prev_date} → {d}: 전 종목 수량이 {ratio:.4f}배로 같이 변함. "
              "설정 단위 변경으로 보인다. 추세 계산 전에 운용사 공지를 확인할 것")
    n = save_holdings(conn, df)
    print(f"  {etf_code} {d}: 주식 {len(df)}종목, 새로 저장 {n}줄")
    return n


def main(argv: list[str]) -> int:
    if not (os.getenv("KRX_ID") and os.getenv("KRX_PW")):
        print("KRX_ID / KRX_PW 가 비어 있습니다. 레포 루트 .env 에 data.krx.co.kr 일반 회원 계정을 넣어 주세요.")
        return 1

    cmd = argv[0] if argv else "today"
    today = datetime.now(KST).date()

    if cmd == "show":
        d = date.fromisoformat(argv[1]) if len(argv) > 1 else latest_trading_day(today)
        for code, name in ETFS.items():
            df = fetch_holdings(code, d)
            print(f"[{code}] {name} {d}: 주식 {len(df)}종목")
            print(df.head(5).to_string(index=False) if len(df) else "  결과 없음")
        return 0

    from db import get_conn

    with get_conn() as conn:
        if cmd == "today":
            d = latest_trading_day(today)
            for code in ETFS:
                collect_day(conn, code, d)
            conn.commit()
        elif cmd == "backfill":
            start = date.fromisoformat(argv[1]) if len(argv) > 1 else date(2026, 9, 30)
            days = trading_days_since(start, latest_trading_day(today))
            for code in ETFS:
                todo = [d for d in days if d not in saved_dates(conn, code)]
                print(f"[{code}] {start} 이후 거래일 {len(days)}일 중 빠진 날 {len(todo)}일")
                for d in todo:
                    collect_day(conn, code, d)
                    conn.commit()  # 중간에 끊겨도 받은 날은 남긴다
                    time.sleep(1)  # KRX 서버 부담을 줄인다
        else:
            print(__doc__)
            return 1
        print(f"ticker 채움: {fill_tickers(conn)}줄")
        conn.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
