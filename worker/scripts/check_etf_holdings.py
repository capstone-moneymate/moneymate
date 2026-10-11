"""액티브 ETF 2개의 구성종목(PDF)을 pykrx로 받아 형식을 확인한다 (1주차 확인용).

실행: cd worker && python scripts/check_etf_holdings.py [YYYYMMDD ...]
      날짜를 안 주면 최근 거래일, 2026-09-30(3분기 말), 2026-06-30(2분기 말)을 조회한다.
필요: pip install pykrx, .env 의 KRX_ID / KRX_PW (data.krx.co.kr 일반 회원가입 계정)

판단은 하지 않는다. 행 수, 주식이 아닌 줄, 소수 수량, 코드 형식을 출력하고 결론은 사람이 내려 docs/findings.md 에 적는다.

pykrx 1.2.9 기준 API:
- KRX 정보데이터시스템이 로그인을 요구해서, 환경변수 KRX_ID·KRX_PW 가 있으면 pykrx가 자동으로 로그인한다.
- stock.get_etf_portfolio_deposit_file(code, "YYYYMMDD"): 구성종목(PDF). index=티커, 컬럼=구성종목명·계약수·금액·시가총액·비중
- stock.get_nearest_business_day_in_a_week("YYYYMMDD"): 그 날짜 이전 가장 가까운 거래일
"""
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

import config  # noqa: E402,F401  레포 루트 .env 를 읽어 KRX_ID·KRX_PW 를 환경변수로 올린다

# 확인 대상 (분담표 B 1주차). KoAct 코드는 2026-10-11 pykrx ETF 목록에서 확인
ETFS = {
    "426030": "TIME 미국나스닥100액티브",
    "0015B0": "KoAct 미국나스닥성장기업액티브",
}
DEFAULT_PAST_DATES = ["20260930", "20260630"]  # 13F 분기 말과 비교할 날짜


def is_non_stock(code: str, name: str) -> bool:
    """현금·선물처럼 주식이 아닌 줄. 주식 코드는 6자리라 그 외 길이는 선물로 본다 (예: NQZ6)."""
    return "현금" in name or len(code) != 6


def describe(code: str, ymd: str) -> None:
    from pykrx import stock

    try:
        df = stock.get_etf_portfolio_deposit_file(code, ymd)
    except Exception as e:  # 한 날짜가 실패해도 나머지는 계속 출력
        print(f"  {ymd}: 조회 실패 {type(e).__name__}: {e}")
        return
    if df is None or len(df) == 0:
        print(f"  {ymd}: 결과 없음 (로그인 실패이거나 그날 데이터 없음)")
        return

    names = df["구성종목명"].astype(str)
    codes = df.index.astype(str)
    non_stock = [(c, n) for c, n in zip(codes, names) if is_non_stock(c, n)]
    stocks = df[[not is_non_stock(c, n) for c, n in zip(codes, names)]]
    fractional = stocks[stocks["계약수"] % 1 != 0]

    print(f"  {ymd}: 전체 {len(df)}줄, 주식 {len(stocks)}줄")
    print(f"    주식이 아닌 줄: {', '.join(f'{c}({n})' for c, n in non_stock) or '없음'}")
    print(f"    소수 수량 주식: {len(fractional)}줄"
          + (f" (예: {fractional.index[0]} {fractional['계약수'].iloc[0]})" if len(fractional) else ""))
    sample = stocks.head(3)
    print("    코드 예시: " + ", ".join(f"{c}={n}" for c, n in zip(sample.index, sample["구성종목명"])))


def main() -> int:
    if not (os.getenv("KRX_ID") and os.getenv("KRX_PW")):
        print("KRX_ID / KRX_PW 가 비어 있습니다.")
        print("data.krx.co.kr 에서 일반 회원가입(아이디·비밀번호)을 하고, 레포 루트 .env 에 넣은 뒤 다시 실행하세요.")
        print("  간편 로그인(네이버 등) 계정은 비밀번호가 없어 pykrx 로그인에 쓸 수 없습니다.")
        return 1

    from pykrx import stock

    dates = sys.argv[1:]
    if not dates:
        latest = stock.get_nearest_business_day_in_a_week(date.today().strftime("%Y%m%d"))
        dates = [latest, *DEFAULT_PAST_DATES]

    for code, name in ETFS.items():
        print("=" * 80)
        print(f"[{code}] {name}")
        print("=" * 80)
        for ymd in dates:
            describe(code, ymd)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
