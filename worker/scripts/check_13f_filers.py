"""큰손 4명의 13F 제출 법인 후보를 SEC EDGAR에서 찾아 전부 출력한다 (1주차 확인용).

실행: cd worker && python scripts/check_13f_filers.py
필요: pip install edgartools, .env 의 EDGAR_IDENTITY ("이름 이메일")

판단은 하지 않는다. 이름이 겹치는 법인을 모두 보여주고, 어느 법인이 맞는지는 사람이 고른다.
확정한 CIK 는 docs/findings.md 와 worker/config.py 의 FILERS 에 반영한다.

edgartools 5.61.1 기준 API:
- get_cik_lookup_data(): SEC 전체 법인명·CIK 목록 (비상장 운용사 포함).
  find_company() 는 상장사 티커 목록만 검색해서 운용사가 빠질 수 있어 쓰지 않는다.
- Company(cik).get_filings(form=..., amendments=False, trigger_full_load=False): 최근 공시 목록
- Filing.obj() -> ThirteenF: report_period, filing_date, total_holdings, management_company_name
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

from config import EDGAR_IDENTITY  # noqa: E402

# docs/findings.md 표의 "후보 법인명"에서 뽑은 검색어. 법인명에 이 단어가 들어가면 전부 출력한다.
SEARCH_TERMS = {
    "buffett": ["BERKSHIRE HATHAWAY"],
    "druckenmiller": ["DUQUESNE FAMILY OFFICE", "DUQUESNE CAPITAL"],
    "thiel": ["THIEL MACRO", "THIEL CAPITAL"],
    "ackman": ["PERSHING SQUARE"],
}
MAX_MATCHES_PER_TERM = 40  # SEC 요청 수 제한용. 넘으면 앞에서부터 자르고 알린다.


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", name.upper())).strip()


def find_entities(lookup, term: str) -> dict[int, list[str]]:
    """법인명에 term 이 들어간 CIK -> [등록된 이름들] (같은 CIK의 옛 이름도 모은다)."""
    key = normalize_name(term)
    hits = lookup[lookup["norm"].str.contains(rf"\b{re.escape(key)}\b", regex=True)]
    result: dict[int, list[str]] = {}
    for row in hits.itertuples():
        result.setdefault(int(row.cik), []).append(row.name)
    return result


def describe(cik: int) -> dict:
    """한 CIK의 기본 정보와 최근 13F-HR 요약."""
    from edgar import Company

    info = {"cik": f"{cik:010d}", "name": "", "location": "", "n_13f_hr": 0,
            "has_13f_nt": False, "period": "", "filed": "", "holdings": "", "manager": "", "error": ""}
    try:
        company = Company(cik)
        info["name"] = company.name
        addr = company.data.business_address
        if addr is not None:
            info["location"] = ", ".join(x for x in (addr.city, addr.state_or_country) if x)

        hr = company.get_filings(form="13F-HR", amendments=False, trigger_full_load=False)
        nt = company.get_filings(form="13F-NT", amendments=False, trigger_full_load=False)
        info["n_13f_hr"] = len(hr)
        info["has_13f_nt"] = len(nt) > 0
        if len(hr) > 0:
            tf = hr.latest(1).obj()
            info["period"] = tf.report_period or ""
            info["filed"] = tf.filing_date or ""
            info["holdings"] = tf.total_holdings if tf.total_holdings is not None else ""
            info["manager"] = tf.management_company_name or ""
    except Exception as e:  # 한 법인이 실패해도 나머지는 계속 출력
        info["error"] = f"{type(e).__name__}: {e}"
    return info


def main() -> int:
    if not EDGAR_IDENTITY.strip():
        print("EDGAR_IDENTITY 가 비어 있습니다.")
        print('레포 루트 .env 에 SEC 신원을 "이름 이메일" 형식으로 넣고 다시 실행하세요.')
        print('  예) EDGAR_IDENTITY=Hong Gildong gildong@example.com')
        print("  근거: https://www.sec.gov/os/accessing-edgar-data")
        return 1
    if not EDGAR_IDENTITY.isascii():
        print("EDGAR_IDENTITY 에 한글 등 영문이 아닌 글자가 있습니다.")
        print("SEC 요청 헤더(User-Agent)에는 영문·숫자만 들어갈 수 있으니 이름을 영문으로 바꿔 주세요.")
        print('  예) EDGAR_IDENTITY=Hong Gildong gildong@example.com')
        return 1

    from edgar import get_cik_lookup_data, set_identity
    import edgar

    set_identity(EDGAR_IDENTITY)
    print(f"edgartools {edgar.__version__}")
    print("SEC 전체 법인 목록 내려받는 중... (처음 한 번, 수십 MB)")
    try:
        lookup = get_cik_lookup_data()
    except Exception as e:
        if "403" in str(e):
            print("SEC가 요청을 거부했습니다 (403 Forbidden, 'Undeclared Automated Tool').")
            print("EDGAR_IDENTITY 의 이메일 도메인을 확인하세요. 2026-10-10 확인 결과 naver.com 은 거부되고")
            print("gmail.com, daum.net, 학교 메일(.ac.kr)은 통과했습니다.")
            return 1
        raise
    lookup["norm"] = lookup["name"].map(normalize_name)
    print(f"법인 {len(lookup):,}건\n")

    for filer_key, terms in SEARCH_TERMS.items():
        print("=" * 100)
        print(f"[{filer_key}] 검색어: {terms}")
        print("=" * 100)
        entities: dict[int, list[str]] = {}
        for term in terms:
            found = find_entities(lookup, term)
            print(f"  '{term}' -> 법인 {len(found)}개")
            if len(found) > MAX_MATCHES_PER_TERM:
                print(f"  (많아서 앞 {MAX_MATCHES_PER_TERM}개만 조회)")
                found = dict(list(found.items())[:MAX_MATCHES_PER_TERM])
            for cik, names in found.items():
                entities.setdefault(cik, []).extend(names)

        if not entities:
            print("  검색 결과 없음\n")
            continue

        rows = [describe(cik) | {"aliases": sorted(set(names))} for cik, names in entities.items()]
        # 13F-HR 을 낸 법인을 위로, 그 안에서는 최근 공시일 순
        rows.sort(key=lambda r: str(r["filed"]), reverse=True)
        rows.sort(key=lambda r: r["n_13f_hr"] == 0)

        for r in rows:
            mark = "13F-HR 있음" if r["n_13f_hr"] else "13F-HR 없음"
            print(f"\n  CIK {r['cik']}  {r['name'] or r['aliases'][0]}  [{mark}]")
            if len(r["aliases"]) > 1 or (r["name"] and r["aliases"][0] != r["name"]):
                print(f"    등록 이름들: {' / '.join(r['aliases'])}")
            if r["location"]:
                print(f"    주소: {r['location']}")
            if r["n_13f_hr"]:
                print(f"    최근 목록의 13F-HR {r['n_13f_hr']}건 | 최근 기간 {r['period']} | 공시일 {r['filed']}"
                      f" | 보유 종목 수 {r['holdings']} | 13F 표지 법인명: {r['manager']}")
            if r["has_13f_nt"]:
                print("    13F-NT(다른 법인이 대신 보고) 제출 이력 있음")
            if r["error"]:
                print(f"    조회 실패: {r['error']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
