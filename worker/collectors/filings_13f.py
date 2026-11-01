"""13F 수집 (A). 큰손 4명의 분기 13F-HR 을 받아 holdings_13f 에 저장한다.

실행 (worker/ 에서):
    python -m collectors.filings_13f                      # 가장 최근 분기와 그 직전 분기를 받아 출력만
    python -m collectors.filings_13f --period 2026-06-30  # 그 분기와 직전 분기
    python -m collectors.filings_13f --save               # DB 에 저장 (cusip_map 도 갱신)
저장한 뒤에는 compute.holdings_change 로 직전 분기 대비 변화를 채운다.

규칙 (docs/conventions.md)
- P5: 주식(Type=Shares)만. 옵션(PutCall 있음)·채권(Principal)은 빼고 저장
- P14: 한 제출 건에 같은 CUSIP 이 여러 줄이면(운용 주체별 등) 합산해 한 줄로
- 정정 신고(13F-HR/A): NEW HOLDINGS(기밀 처리 해제 등으로 추가 공개된 종목)는 원본에 더하고,
  RESTATEMENT(전체 다시 제출)는 원본을 대신한다. 유형이 비어 있는 정정은 RESTATEMENT 로 본다
- config.FILERS 의 extra_ciks 도 같은 큰손으로 수집한다 (행은 실제 제출 법인 CIK 로 저장)
- 티커: cusip_map 캐시 → edgartools 의 Ticker → OpenFIGI 순. 못 찾으면 NULL

edgartools 5.61.1 기준 API:
- Company(cik).get_filings(form=..., trigger_full_load=False): Filing 목록. Filing.period_of_report 로 분기를 거른다
- Filing.obj() -> ThirteenF: infotable(DataFrame: Issuer, Cusip, SharesPrnAmount, Type, PutCall, Ticker ...),
  amendment_type('NEW HOLDINGS' / 'RESTATEMENT' / None), filing_date, accession_number
"""
import argparse
import sys
import time
import warnings
from dataclasses import dataclass
from datetime import date

import pandas as pd
import requests

import config
from common.normalize import normalize_us_ticker
from common.quarters import latest_quarter_end, parse_quarter_end, prev_quarter_end

OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"


@dataclass
class Report:
    """13F-HR 또는 13F-HR/A 한 건."""
    accession_no: str
    filed_at: date
    is_amendment: bool
    amendment_type: str | None  # 'NEW HOLDINGS' / 'RESTATEMENT' / None
    infotable: pd.DataFrame


def shares_by_cusip(infotable: pd.DataFrame) -> pd.DataFrame:
    """P5 필터 후 P14 합산. 결과 열: cusip, issuer_name, edgar_ticker, shares.
    보유가 없는 분기에 내는 빈 줄(CUSIP 000000000, 0주. 틸 2026-03-31분)은 뺀다."""
    t = infotable.copy()
    put_call = t["PutCall"].fillna("").str.strip()
    t = t[(t["Type"] == "Shares") & (put_call == "") & (t["SharesPrnAmount"] > 0)
          & (t["Cusip"].str.strip() != "000000000")]
    if t.empty:
        return pd.DataFrame(columns=["cusip", "issuer_name", "edgar_ticker", "shares"])
    t["Cusip"] = t["Cusip"].str.strip().str.upper()
    out = t.groupby("Cusip", as_index=False, sort=True).agg(
        issuer_name=("Issuer", "first"),
        edgar_ticker=("Ticker", "first"),
        shares=("SharesPrnAmount", "sum"),
    )
    return out.rename(columns={"Cusip": "cusip"})


def merge_reports(reports: list[Report]) -> tuple[pd.DataFrame, Report]:
    """한 법인·한 분기의 원본과 정정 신고들을 합친다. (보유 표, 대표 신고) 를 돌려준다.

    대표 신고 = 가장 늦은 원본/RESTATEMENT. NEW HOLDINGS 는 대표 신고보다 늦게 낸 것만 더한다
    (대표보다 먼저 낸 NEW HOLDINGS 는 그 뒤의 RESTATEMENT 에 이미 들어 있다고 본다).
    """
    bases = [r for r in reports if not r.is_amendment or r.amendment_type != "NEW HOLDINGS"]
    if not bases:
        raise ValueError("원본 13F-HR 이 없다 (정정 신고만 있음)")
    base = max(bases, key=lambda r: (r.filed_at, r.is_amendment))
    adds = [r for r in reports
            if r.is_amendment and r.amendment_type == "NEW HOLDINGS" and r.filed_at >= base.filed_at
            and r is not base]
    table = pd.concat([base.infotable] + [r.infotable for r in adds], ignore_index=True)
    return shares_by_cusip(table), base


def clean_ticker(raw) -> str | None:
    """edgartools·OpenFIGI 티커를 P1 형식으로. 형식이 안 맞으면 None."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)) or not str(raw).strip():
        return None
    try:
        return normalize_us_ticker(str(raw))
    except ValueError:
        return None


# ------------------------------------------------------------------
# 외부 호출 (SEC, OpenFIGI)
# ------------------------------------------------------------------

def fetch_reports(cik: str, period: date) -> list[Report]:
    """한 법인의 그 분기 13F-HR·13F-HR/A 를 모두 받는다. 없으면 빈 목록."""
    from edgar import Company

    company = Company(cik)
    reports = []
    for form in ("13F-HR", "13F-HR/A"):
        for f in company.get_filings(form=form, trigger_full_load=False):
            if str(f.period_of_report) != period.isoformat():
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # Value(평가액) 단위 경고. 수량만 쓰므로 무시
                tf = f.obj()
            if not tf.has_infotable:
                continue
            reports.append(Report(
                accession_no=f.accession_no,
                filed_at=date.fromisoformat(str(f.filing_date)),
                is_amendment=form == "13F-HR/A",
                amendment_type=tf.amendment_type if form == "13F-HR/A" else None,
                infotable=tf.infotable,
            ))
    return reports


def latest_period(cik: str) -> date:
    """그 법인이 낸 가장 최근 13F-HR 분기."""
    from edgar import Company

    f = Company(cik).get_filings(form="13F-HR", trigger_full_load=False).latest(1)
    return date.fromisoformat(str(f.period_of_report))


def openfigi_tickers(cusips: list[str]) -> dict[str, str | None]:
    """OpenFIGI 로 CUSIP -> 미국 티커. 키가 없으면 10개씩, 분당 25회 한도라 사이를 띄운다."""
    headers = {"Content-Type": "application/json"}
    batch = 10
    pause = 2.5
    if config.OPENFIGI_API_KEY:
        headers["X-OPENFIGI-APIKEY"] = config.OPENFIGI_API_KEY
        batch, pause = 100, 0.3
    result: dict[str, str | None] = {}
    for i in range(0, len(cusips), batch):
        chunk = cusips[i:i + batch]
        body = [{"idType": "ID_CUSIP", "idValue": c, "exchCode": "US"} for c in chunk]
        resp = requests.post(OPENFIGI_URL, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        for cusip, item in zip(chunk, resp.json()):
            data = item.get("data") or []
            result[cusip] = clean_ticker(data[0].get("ticker")) if data else None
        time.sleep(pause)
    return result


# ------------------------------------------------------------------
# 수집 → 저장
# ------------------------------------------------------------------

def collect_period(filer_key: str, period: date) -> list[dict]:
    """한 큰손·한 분기의 저장할 행 목록. 법인(cik)마다 따로 만든다. 티커는 아직 edgar_ticker 만."""
    filer = config.FILERS[filer_key]
    rows = []
    for cik in [filer["cik"], *filer.get("extra_ciks", [])]:
        reports = fetch_reports(cik, period)
        if not reports:
            continue
        table, base = merge_reports(reports)
        for r in table.itertuples(index=False):
            rows.append({
                "filer_key": filer_key, "filer_cik": cik, "filer_name": filer["name"],
                "period_end": period, "filed_at": base.filed_at, "accession_no": base.accession_no,
                "cusip": r.cusip, "issuer_name": r.issuer_name, "edgar_ticker": r.edgar_ticker,
                "shares": int(r.shares),
            })
    return rows


def resolve_tickers(conn, rows: list[dict]) -> None:
    """rows 의 ticker 를 채우고 cusip_map 을 갱신한다 (cusip_map → edgartools → OpenFIGI)."""
    cusips = sorted({r["cusip"] for r in rows})
    cached = dict(conn.execute(
        "SELECT cusip, ticker FROM cusip_map WHERE cusip = ANY(%s)", (cusips,)
    ).fetchall())
    new_map: dict[str, tuple[str | None, str, str | None]] = {}  # cusip -> (ticker, source, issuer)
    for r in rows:
        c = r["cusip"]
        if c in cached or c in new_map:
            continue
        t = clean_ticker(r["edgar_ticker"])
        if t:
            new_map[c] = (t, "edgartools", r["issuer_name"])
    missing = [c for c in cusips if c not in cached and c not in new_map]
    if missing:
        issuers = {r["cusip"]: r["issuer_name"] for r in rows}
        for c, t in openfigi_tickers(missing).items():
            new_map[c] = (t, "openfigi", issuers.get(c))
    for c, (t, source, issuer) in new_map.items():
        conn.execute(
            """INSERT INTO cusip_map (cusip, ticker, issuer_name, source) VALUES (%s, %s, %s, %s)
               ON CONFLICT (cusip) DO UPDATE SET ticker = EXCLUDED.ticker, issuer_name = EXCLUDED.issuer_name,
                   source = EXCLUDED.source, resolved_at = now()""",
            (c, t, issuer, source),
        )
        cached[c] = t
    for r in rows:
        r["ticker"] = cached.get(r["cusip"])


def save_rows(conn, rows: list[dict]) -> None:
    """같은 (법인, 분기, CUSIP) 이 있으면 수량·티커를 새 값으로 (정정 신고 반영).
    prev_shares·chg_pct·change_type 은 holdings_change 가 다시 채운다."""
    for r in rows:
        conn.execute(
            """INSERT INTO holdings_13f (filer_key, filer_cik, filer_name, period_end, filed_at, accession_no,
                   cusip, ticker, issuer_name, shares)
               VALUES (%(filer_key)s, %(filer_cik)s, %(filer_name)s, %(period_end)s, %(filed_at)s,
                   %(accession_no)s, %(cusip)s, %(ticker)s, %(issuer_name)s, %(shares)s)
               ON CONFLICT (filer_cik, period_end, cusip) DO UPDATE SET
                   filed_at = EXCLUDED.filed_at, accession_no = EXCLUDED.accession_no,
                   ticker = EXCLUDED.ticker, issuer_name = EXCLUDED.issuer_name,
                   shares = EXCLUDED.shares, collected_at = now()""",
            r,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="큰손 13F 수집")
    parser.add_argument("--period", help="분기 말 (예: 2026-06-30). 없으면 버핏의 가장 최근 13F 분기")
    parser.add_argument("--filer", choices=sorted(config.FILERS), help="한 명만 받기")
    parser.add_argument("--save", action="store_true", help="DB 에 저장")
    args = parser.parse_args(argv)

    if not config.EDGAR_IDENTITY.strip() or not config.EDGAR_IDENTITY.isascii():
        print('EDGAR_IDENTITY 가 비었거나 영문이 아닙니다. .env 에 "영문이름 이메일" 형식으로 넣어 주세요.')
        return 1
    from edgar import set_identity
    set_identity(config.EDGAR_IDENTITY)

    period = parse_quarter_end(args.period) if args.period else latest_quarter_end(
        latest_period(config.FILERS["buffett"]["cik"]))
    periods = [prev_quarter_end(period), period]
    filer_keys = [args.filer] if args.filer else list(config.FILERS)

    all_rows = []
    for key in filer_keys:
        for p in periods:
            rows = collect_period(key, p)
            ciks = sorted({r["filer_cik"] for r in rows})
            print(f"{key:14s} {p}  {len(rows):4d}종목  법인 {ciks or '(제출 없음)'}")
            all_rows.extend(rows)

    if not args.save:
        print("\n출력만 했습니다. 저장하려면 --save 를 붙이세요.")
        return 0

    from db import get_conn
    with get_conn() as conn:
        resolve_tickers(conn, all_rows)
        save_rows(conn, all_rows)
    no_ticker = sorted({(r["cusip"], r["issuer_name"]) for r in all_rows if not r["ticker"]})
    print(f"\n저장 {len(all_rows)}행. 티커 못 찾음 {len(no_ticker)}개: {no_ticker[:10]}")
    print("다음: python -m compute.holdings_change --period", period)
    return 0


if __name__ == "__main__":
    sys.exit(main())
