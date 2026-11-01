"""1차 자료 수집 (C). 네이버 검색 결과 대신 공시·기관 발표를 쓴다 (기술확정안 "1차 자료 선별").

- DART OpenAPI list.json: 국내 공시. 거래소공시(I)·주요사항보고서(B)만 받고, source_select.dart_category 로 거른다.
  회사를 미리 고르지 않는다 (유가증권·코스닥 상장사 전체).
- SEC 8-K (edgartools): 탭 2 종목만. Item 2.02(실적)·1.01(중요 계약)만.
- 거시 발표: collectors/macro_calendar.csv 의 예정된 발표 (FOMC, 한은 기준금리). 금리 값은 한은은 ECOS, 미국은 FRED 로 채운다.

본문은 저장하지 않는다 (CLAUDE.md 9). 원문 링크·날짜·필요한 숫자만 저장한다.

실행 (국내는 장 마감 후 16:00, 미국은 다음 날 아침 08:00):
  cd worker && python collectors/sources.py dart 2026-10-27
  cd worker && python collectors/sources.py sec 2026-10-27 NVDA AAPL
  cd worker && python collectors/sources.py macro 2026-10-22
  끝에 --save 를 붙이면 raw_sources 에 저장한다 (안 붙이면 화면 출력만)
필요: .env 의 DART_API_KEY (opendart.fss.or.kr), ECOS_API_KEY (ecos.bok.or.kr), EDGAR_IDENTITY
저장: raw_sources 테이블 (A에게 003 마이그레이션 요청 중, docs/modules/sources.md).
"""
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

import config  # noqa: E402  .env 를 읽는다
from common.normalize import normalize_kr_code, normalize_us_ticker  # noqa: E402
from compute.source_select import dart_category, sec_8k_category  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DART_VIEW_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={}"
# /1/100/ = 1~100번째 줄. 처음에 /1/10/ 이라 14일치 중 결정일 이후가 잘려 판정을 못 했다 (2026-10-28 실호출로 발견)
ECOS_URL = "https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/100/722Y001/D/{start}/{end}/0101000"
MACRO_CALENDAR = Path(__file__).resolve().parent / "macro_calendar.csv"


@dataclass
class Source:
    """raw_sources 한 줄."""
    source_type: str            # dart / sec_8k / macro
    source_key: str             # DART rcept_no, 8-K accession, 거시 event_id. (source_type, source_key) 가 유일
    category: str               # supply_contract / earnings / buyback / capex / material_agreement / fomc / bok_rate
    title: str
    url: str
    published_date: date        # 발표일 (그 시장 날짜)
    published_at: datetime | None = None  # 발표 시각(aware). DART 는 시각을 주지 않아 None
    issuer_name: str | None = None
    ticker: str | None = None   # 반응을 볼 대상: 국내 6자리 / 미국 티커 / 지수 키(KS11·US500)
    market: str | None = None   # KR / US / INDEX
    numbers: dict = field(default_factory=dict)  # 카드에 쓸 숫자 (예: 금리 전·후)


# ------------------------------------------------------------------
# DART
# ------------------------------------------------------------------
def dart_rows_to_sources(rows: list[dict]) -> list[Source]:
    """list.json 의 list 항목 → 거르기를 통과한 Source. 유가(Y)·코스닥(K) 상장사만."""
    out = []
    for r in rows:
        if r.get("corp_cls") not in ("Y", "K") or not r.get("stock_code", "").strip():
            continue
        cat = dart_category(r["report_nm"])
        if cat is None:
            continue
        out.append(Source(
            source_type="dart",
            source_key=r["rcept_no"],
            category=cat,
            title=f'{r["corp_name"]} {r["report_nm"].strip()}',
            url=DART_VIEW_URL.format(r["rcept_no"]),
            published_date=datetime.strptime(r["rcept_dt"], "%Y%m%d").date(),
            issuer_name=r["corp_name"],
            ticker=normalize_kr_code(r["stock_code"]),
            market="KR",
        ))
    return out


def fetch_dart(d: date, api_key: str | None = None) -> list[Source]:
    """그날 접수된 거래소공시(I)·주요사항보고서(B) 전체를 페이지 넘기며 받아 거른다."""
    api_key = api_key or os.getenv("DART_API_KEY")
    if not api_key:
        raise RuntimeError("DART_API_KEY 가 비어 있습니다 (opendart.fss.or.kr 인증키 신청 후 .env 에 넣기)")
    ymd = d.strftime("%Y%m%d")
    rows: list[dict] = []
    for ty in ("I", "B"):
        page = 1
        while True:
            res = requests.get(DART_LIST_URL, params={
                "crtfc_key": api_key, "bgn_de": ymd, "end_de": ymd,
                "pblntf_ty": ty, "page_no": page, "page_count": 100,
            }, timeout=20).json()
            if res.get("status") == "013":  # 조회된 데이터 없음
                break
            if res.get("status") != "000":
                raise RuntimeError(f"DART 오류 {res.get('status')}: {res.get('message')}")
            rows += res["list"]
            if page >= int(res["total_page"]):
                break
            page += 1
    return dart_rows_to_sources(rows)


# ------------------------------------------------------------------
# SEC 8-K
# ------------------------------------------------------------------
def fetch_sec_8k(d: date, tickers: list[str]) -> list[Source]:
    """탭 2 종목의 그날(미국 날짜) 8-K 중 Item 2.02·1.01. 접수 시각(acceptance)으로 반응일을 정한다."""
    from edgar import Company, set_identity

    if not config.EDGAR_IDENTITY:
        raise RuntimeError("EDGAR_IDENTITY 가 비어 있습니다 (.env, 영문 이름 + gmail)")
    set_identity(config.EDGAR_IDENTITY)
    out = []
    for raw in tickers:
        t = normalize_us_ticker(raw)
        filings = Company(t).get_filings(form="8-K", filing_date=d.isoformat(), amendments=False)
        for f in filings:
            items = getattr(f, "items", None) or getattr(f.obj(), "items", [])
            cat = sec_8k_category(items)
            if cat is None:
                continue
            accepted = getattr(f, "acceptance_datetime", None) or f.header.acceptance_datetime
            if isinstance(accepted, str):
                accepted = datetime.fromisoformat(accepted.replace("Z", "+00:00"))
            out.append(Source(
                source_type="sec_8k",
                source_key=f.accession_no,
                category=cat,
                title=f"{f.company} 8-K Item {', '.join(items) if isinstance(items, list) else items}",
                url=f.homepage_url,
                published_date=d,
                published_at=accepted if accepted and accepted.tzinfo else None,
                issuer_name=f.company,
                ticker=t,
                market="US",
            ))
    return out


# ------------------------------------------------------------------
# 거시 발표
# ------------------------------------------------------------------
def load_macro_calendar(path: Path = MACRO_CALENDAR) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def macro_sources_on(d: date, calendar: list[dict]) -> list[Source]:
    """발표 현지 날짜가 d 인 예정 발표. verified=N(공식 일정 미확인)도 넣되 numbers 에 표시한다."""
    out = []
    for row in calendar:
        at = datetime.fromisoformat(row["announce_at"])
        if at.date() != d:
            continue
        out.append(Source(
            source_type="macro",
            source_key=row["event_id"],
            category=row["kind"],
            title=row["title"],
            url=row["url"],
            published_date=d,
            published_at=at,
            ticker=row["target"],
            market="INDEX",
            numbers={"calendar_verified": row["verified"] == "Y"},
        ))
    return out


def rate_change(series: list[tuple[date, float]], d: date, after_from: date) -> dict | None:
    """일별 금리 (날짜, 값) → 결정일 d 의 {rate_before, rate_after, decision}.

    rate_before: d 전날까지의 마지막 값. rate_after: after_from 부터의 첫 값.
    decision: hike / cut / hold (개념 사전 rate_hike / rate_cut / rate_hold 와 맞춘다).
    """
    series = sorted(series)
    before = [v for t, v in series if t < d]
    after = [v for t, v in series if t >= after_from]
    if not before or not after:
        return None
    b, a = before[-1], after[0]
    return {"rate_before": b, "rate_after": a, "decision": "hike" if a > b else "cut" if a < b else "hold"}


def bok_rate_change(rows: list[dict], d: date) -> dict | None:
    """ECOS 기준금리 일별 행(TIME, DATA_VALUE). ECOS 는 결정 당일부터 새 금리가 찍힌다 (2026-07-16 인상으로 확인)."""
    series = [(datetime.strptime(r["TIME"], "%Y%m%d").date(), float(r["DATA_VALUE"])) for r in rows]
    return rate_change(series, d, after_from=d)


def fed_rate_change(series: list[tuple[date, float]], d: date) -> dict | None:
    """FRED 정책금리 목표 상단(DFEDTARU). 결정 다음 날부터 새 목표가 찍힌다 (2026-09-16 결정 → 9/17 변경으로 확인)."""
    return rate_change(series, d, after_from=d + timedelta(days=1))


def fetch_fed_rate(d: date) -> dict | None:
    """FinanceDataReader 로 FRED 목표 범위(상단 DFEDTARU·하단 DFEDTARL)를 받아 FOMC 결정일 d 를 판정한다. 키 필요 없음."""
    import FinanceDataReader as fdr

    df = fdr.DataReader("FRED:DFEDTARU,DFEDTARL", (d - timedelta(days=10)).isoformat(),
                        (d + timedelta(days=5)).isoformat()).dropna()
    upper = [(ts.date(), float(v)) for ts, v in df["DFEDTARU"].items()]
    change = fed_rate_change(upper, d)
    if change:
        after = df[df.index.date > d]
        change["range_after"] = f'{after["DFEDTARL"].iloc[0]:.2f}~{after["DFEDTARU"].iloc[0]:.2f}'
    return change


def fetch_bok_rate(d: date, api_key: str | None = None) -> dict | None:
    api_key = api_key or os.getenv("ECOS_API_KEY")
    if not api_key:
        raise RuntimeError("ECOS_API_KEY 가 비어 있습니다 (ecos.bok.or.kr 인증키 신청 후 .env 에 넣기)")
    url = ECOS_URL.format(key=api_key, start=(d - timedelta(days=10)).strftime("%Y%m%d"),
                          end=(d + timedelta(days=3)).strftime("%Y%m%d"))
    return bok_rate_change(ecos_rows(requests.get(url, timeout=20).json()), d)


def ecos_rows(res: dict) -> list[dict]:
    """ECOS 응답 → 행 목록. 오류는 StatisticSearch 대신 RESULT 로 온다 (2026-10-28 실호출 확인).

    INFO-200(해당 데이터 없음)은 빈 목록, 그 외(INFO-100 인증키 오류, 호출 한도 등)는 예외로 멈춘다.
    조용히 None 을 돌려주면 한은 결정이 빈 채로 저장되기 때문이다 (DART 의 status 검사와 같은 이유).
    """
    if "RESULT" in res:
        code, msg = res["RESULT"].get("CODE"), res["RESULT"].get("MESSAGE")
        if code == "INFO-200":
            return []
        raise RuntimeError(f"ECOS 오류 {code}: {msg}")
    return res.get("StatisticSearch", {}).get("row", [])


def fetch_macro(d: date) -> list[Source]:
    out = macro_sources_on(d, load_macro_calendar())
    for s in out:
        if s.category == "bok_rate" and os.getenv("ECOS_API_KEY"):
            s.numbers.update(fetch_bok_rate(d) or {})
        elif s.category == "fomc":
            # 결정 다음 날 값이 있어야 판정된다. 미국 다음 날 아침(KST) 수집이면 FRED 반영 전일 수 있어 비면
            # 다음 날 같은 날짜로 다시 수집한다 (save_sources 가 numbers 를 합쳐 갱신. run_daily 에서 전날 거시도 다시 돌릴 것)
            s.numbers.update(fetch_fed_rate(d) or {})
    return out


# ------------------------------------------------------------------
# 저장
# ------------------------------------------------------------------
def save_sources(conn, sources: list[Source]) -> int:
    """raw_sources 에 넣는다. 새로 넣거나 numbers 가 바뀐 줄 수를 돌려준다.

    이미 있는 (source_type, source_key) 는 다른 칸은 그대로 두고 numbers 만 합친다 (jsonb ||, 새 값이 우선).
    FOMC 는 결정 다음 날 아침에 FRED 가 아직 안 바뀌어 금리 값이 비어 저장될 수 있어서,
    다음 날 같은 발표를 다시 수집하면 rate_before·rate_after·decision 이 채워지게 하려는 것이다.
    새 값이 이미 다 들어 있으면(@>) 쓰지 않는다.
    """
    n = 0
    with conn.cursor() as cur:
        for s in sources:
            cur.execute(
                """
                INSERT INTO raw_sources (source_type, source_key, category, title, url, issuer_name,
                                         ticker, market, published_date, published_at, numbers)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_type, source_key) DO UPDATE
                    SET numbers = raw_sources.numbers || EXCLUDED.numbers
                    WHERE NOT raw_sources.numbers @> EXCLUDED.numbers
                """,
                (s.source_type, s.source_key, s.category, s.title, s.url, s.issuer_name,
                 s.ticker, s.market, s.published_date, s.published_at, json.dumps(s.numbers)),
            )
            n += cur.rowcount
    return n


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    kind, d = argv[0], date.fromisoformat(argv[1])
    if kind == "dart":
        sources = fetch_dart(d)
    elif kind == "sec":
        sources = fetch_sec_8k(d, [a for a in argv[2:] if not a.startswith("--")])
    elif kind == "macro":
        sources = fetch_macro(d)
    else:
        print(__doc__)
        return 1
    for s in sources:
        print(f"[{s.category}] {s.ticker} {s.title}  {s.url}  {s.numbers or ''}")
    print(f"거르기 통과 {len(sources)}건")
    if "--save" not in argv:
        # get_conn() 은 DB가 꺼져 있으면 오래 기다린다 (2026-10-28 확인). 저장은 명시할 때만
        print("저장하려면 --save 를 붙인다 (DB 실행 + 003 마이그레이션 필요)")
        return 0
    from db import get_conn

    with get_conn() as conn:
        print(f"raw_sources 새로 저장·숫자 갱신 {save_sources(conn, sources)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
