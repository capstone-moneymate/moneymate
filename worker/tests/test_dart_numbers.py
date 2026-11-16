"""dart_numbers.py: DART 공시 원문 표에서 숫자 뽑기 (네트워크 없이).

표 모양은 2026-11-16 실제 공시(영업(잠정)실적, 손익구조30%변동, 단일판매ㆍ공급계약, 자기주식취득결정,
주식소각결정, 신규시설투자)의 서식을 따른 가짜 값이다. 기대값은 표에서 손으로 읽은 값이다.
"""
import io
import zipfile

import pytest

from collectors import dart_numbers as dn
from collectors.dart_numbers import (
    decode,
    direction,
    iso_date,
    label_values,
    num,
    parse_numbers,
    table_rows,
)


def _doc(*rows: list[str]) -> str:
    """칸 목록 → DART 원문처럼 <TABLE><TR><TD> (칸 이름을 섞어 TU·TE 도 읽는지 본다)."""
    tags = ["TD", "TU", "TE", "TH"]
    trs = "".join("<TR>" + "".join(f"<{tags[i % 4]} WIDTH='10'>{c}</{tags[i % 4]}>" for i, c in enumerate(r))
                  + "</TR>" for r in rows)
    return f"<html><head><meta content=\"text/html; charset=euc-kr\"></head><BODY><TABLE>{trs}</TABLE></BODY></html>"


EARNINGS = _doc(
    ["당기실적", "2026-07-01", "~", "2026-09-30"],
    ["전기실적", "2026-04-01", "~", "2026-06-30"],
    ["1. 연결실적내용", "단위 : 억원, %"],
    ["구분", "당기실적", "전기실적", "전기대비", "전년동기실적", "전년동기대비"],
    ["(26년 3분기)", "(26년 2분기)", "증감율(%)", "흑자적자전환여부", "(25년 3분기)", "증감율(%)", "흑자적자전환여부"],
    ["매출액", "당해실적", "1,200", "1,000", "20.0", "-", "1,500", "-20.0", "-"],
    ["누계실적", "3,000", "-", "-", "-", "2,800", "7.1", "-"],
    ["영업이익", "당해실적", "-30", "50", "-", "적자전환", "40", "-", "적자전환"],
    ["누계실적", "100", "-", "-", "-", "90", "11.1", "-"],
    ["법인세비용차감전계속사업이익", "당해실적", "1", "2", "-50.0", "-", "3", "-66.7", "-"],
    ["당기순이익", "당해실적", "△5", "-8", "-", "적자지속", "10", "-", "적자전환"],
    ["지배기업 소유주지분 순이익", "당해실적", "7", "-", "-", "-", "-", "-", "-"],
)


def test_earnings_reads_current_quarter_and_direction():
    n = parse_numbers("earnings", "테스트 연결재무제표기준영업(잠정)실적(공정공시)", EARNINGS)
    assert n["실적기간"] == "2026-07-01~2026-09-30"
    assert n["단위"] == "억원"
    # 매출액: 1,200 vs 전년동기 1,500 → -20.0% 감소, 전기 1,000 대비 +20.0% 증가 (누계실적 줄은 안 읽는다)
    assert n["매출액"] == 1200 and n["매출액 전년동기"] == 1500
    assert n["매출액 전년동기대비(%)"] == -20.0 and n["매출액 전년동기대비 방향"] == "감소"
    assert n["매출액 전기대비(%)"] == 20.0 and n["매출액 전기대비 방향"] == "증가"
    # 영업이익: 증감률 '-' 이고 전환 칸이 '적자전환'
    assert n["영업이익"] == -30 and "영업이익 전년동기대비(%)" not in n
    assert n["영업이익 전년동기대비 방향"] == "적자전환"
    # 당기순이익: △5 = -5, 전기 대비 '적자지속'
    assert n["당기순이익"] == -5 and n["당기순이익 전기대비 방향"] == "적자지속"
    # 세 항목만 넣는다 (법인세차감전·지배기업 순이익은 안 넣음)
    assert not any("법인세" in k or "지배" in k for k in n)


def test_earnings_all_dash_is_empty():
    doc = _doc(["1. 연결실적내용", "단위 : 백만원, %"],
               ["매출액", "당해실적", "-", "-", "-", "-", "-", "-", "-"],
               ["영업이익", "당해실적", "-", "-", "-", "-", "-", "-", "-"])
    assert parse_numbers("earnings", "테스트 영업(잠정)실적(공정공시)", doc) == {}


def test_change30_compares_with_previous_period_and_cause():
    doc = _doc(
        ["1. 재무제표의 종류", "연결"],
        ["2. 결산기간", "당해사업연도", "직전사업연도"],
        ["- 시작일", "2026-07-01", "2026-04-01"],
        ["- 종료일", "2026-09-30", "2026-06-30"],
        ["3. 매출액 또는 손익구조 변동내용(단위:천원)", "당해사업연도", "직전사업연도", "증감금액", "증감비율(%)", "흑자적자전환여부"],
        ["- 매출액", "80,000", "100,000", "-20,000", "-20.0", "-"],
        ["- 영업이익", "-1,000", "2,000", "-3,000", "-", "적자전환"],
        ["- 당기순이익", "500", "400", "100", "25.0", "-"],
        ["5. 매출액 또는 손익구조 변동 주요원인", "원재료 가격 상승에 따른 원가율 악화" + "가" * 100],
    )
    n = parse_numbers("earnings", "테스트 매출액또는손익구조30%(대규모법인은15%)이상변동", doc)
    assert n["단위"] == "천원"
    assert n["당해기간"] == "2026-07-01~2026-09-30" and n["직전기간"] == "2026-04-01~2026-06-30"
    assert n["매출액"] == 80000 and n["매출액 직전사업연도"] == 100000
    assert n["매출액 증감비율(%)"] == -20.0 and n["매출액 방향"] == "감소"
    assert n["영업이익 방향"] == "적자전환"
    assert n["당기순이익 방향"] == "증가"
    # 원인 글은 TEXT_MAX 로 자른다 (본문 저장 금지)
    assert n["변동 주요원인"].startswith("원재료 가격 상승") and len(n["변동 주요원인"]) == dn.TEXT_MAX + 1


SUPPLY = _doc(
    ["자회사인", "테스트건설(주)", "의 주요경영사항신고"],
    ["1. 판매ㆍ공급계약 구분", "공사수주"],
    ["- 체결계약명", "물류센터 신축공사"],
    ["2. 계약내역", "계약금액(원)", "50,000,000,000"],
    ["최근매출액(원)", "400,000,000,000"],
    ["매출액대비(%)", "12.5"],
    ["대규모법인여부", "해당"],
    ["3. 계약상대", "테스트물류(주)"],
    ["- 회사와의 관계", "-"],
    ["4. 판매ㆍ공급지역", "경기도"],
    ["5. 계약기간", "시작일", "2026-11-05"],
    ["종료일", "2028-06-30"],
    ["6. 주요 계약조건", "계약금ㆍ선급금 유무", "무"],
)


def test_supply_contract_amount_ratio_and_subsidiary():
    n = parse_numbers("supply_contract", "테스트 단일판매ㆍ공급계약체결(자회사의 주요경영사항)", SUPPLY)
    assert n == {
        "체결계약명": "물류센터 신축공사",
        "계약금액(원)": 50_000_000_000,
        "최근매출액(원)": 400_000_000_000,
        "매출액대비(%)": 12.5,
        "계약상대": "테스트물류(주)",
        "공급지역": "경기도",
        "계약 시작일": "2026-11-05",
        "계약 종료일": "2028-06-30",
        "자회사": "테스트건설(주)",
    }


def test_buyback_acquisition_uses_its_own_period():
    doc = _doc(
        ["1. 취득예정주식(주)", "보통주식", "100,000"],
        ["기타주식", "-"],
        ["2. 취득예정금액(원)", "보통주식", "1,000,000,000"],
        ["3. 취득예상기간", "시작일", "2026년 11월 03일"],
        ["종료일", "2027년 02월 02일"],
        ["4. 보유예상기간", "시작일", "-"],
        ["종료일", "-"],
        ["5. 취득목적", "주주가치 제고"],
        ["6. 취득방법", "장내 직접취득"],
    )
    n = parse_numbers("buyback", "테스트 주요사항보고서(자기주식취득결정)", doc)
    assert n == {"취득예정주식(주)": 100_000, "취득예정금액(원)": 1_000_000_000, "취득 시작일": "2026-11-03",
                 "취득 종료일": "2027-02-02", "취득목적": "주주가치 제고", "취득방법": "장내 직접취득"}


def test_cancel_ratio_is_computed_by_code():
    doc = _doc(
        ["1. 소각할 주식의 종류와 수", "보통주식 (주)", "2,000,000"],
        ["종류주식 (주)", "-"],
        ["2. 발행주식 총수", "보통주식 (주)", "80,000,000"],
        ["3. 1주당 가액(원)", "500"],
        ["4. 소각예정금액(원)", "30,000,000,000"],
        ["6. 소각할 주식의 취득방법", "기취득 자기주식"],
        ["7. 소각 예정일", "2026-11-20"],
    )
    n = parse_numbers("buyback", "테스트 주식소각결정", doc)
    # 2,000,000 ÷ 80,000,000 × 100 = 2.5
    assert n["발행주식대비(%)"] == 2.5
    assert n["소각주식(주)"] == 2_000_000 and n["발행주식총수(주)"] == 80_000_000
    assert n["소각예정금액(원)"] == 30_000_000_000 and n["소각예정일"] == "2026-11-20"
    assert n["취득방법"] == "기취득 자기주식"


def test_cancel_preferred_only():
    doc = _doc(
        ["1. 소각할 주식의 종류와 수", "보통주식 (주)", "-"],
        ["종류주식 (주)", "8,000"],
        ["2. 발행주식 총수", "보통주식 (주)", "50,000,000"],
        ["종류주식 (주)", "16,000,000"],
        ["4. 소각예정금액(원)", "300,000,000"],
    )
    n = parse_numbers("buyback", "테스트 주식소각결정", doc)
    # 8,000 ÷ 16,000,000 × 100 = 0.05. 보통주 키는 넣지 않는다
    assert n == {"종류주식 소각주식(주)": 8000, "종류주식 발행주식총수(주)": 16_000_000,
                 "종류주식 발행주식대비(%)": 0.05, "소각예정금액(원)": 300_000_000}


def test_capex_with_hidden_amount():
    doc = _doc(
        ["1. 투자구분", "신규시설투자"],
        ["- 투자대상", "반도체 패키지 기판 공장"],
        ["2. 투자내역", "투자금액(원)", "-"],
        ["자기자본(원)", "1,000,000,000,000"],
        ["자기자본대비(%)", "-"],
        ["3. 투자목적", "생산능력 확대"],
        ["4. 투자기간", "시작일", "2026-11-03"],
        ["종료일", "2028-12-31"],
    )
    n = parse_numbers("capex", "테스트 신규시설투자등", doc)
    # 공시 유보로 투자금액이 '-' 면 넣지 않는다
    assert n == {"투자대상": "반도체 패키지 기판 공장", "자기자본(원)": 1_000_000_000_000,
                 "투자목적": "생산능력 확대", "투자 시작일": "2026-11-03", "투자 종료일": "2028-12-31"}


def test_unknown_category_or_layout_is_empty():
    assert parse_numbers("fomc", "x", SUPPLY) == {}
    assert parse_numbers("supply_contract", "x", "<html>표 없음</html>") == {}


@pytest.mark.parametrize("raw,expected", [
    ("83,098,217,738", 83_098_217_738), ("-4.2", -4.2), ("△12", -12), ("(3,000)", -3000),
    ("24.0", 24.0), ("-", None), ("", None), ("해당", None), (None, None),
])
def test_num(raw, expected):
    assert num(raw) == expected


def test_iso_date_and_direction():
    assert iso_date("2026년 11월 3일") == "2026-11-03"
    assert iso_date("2026-11-03") == "2026-11-03"
    assert iso_date("-") is None
    assert direction(3.1, "-") == "증가" and direction(-0.5, None) == "감소" and direction(0, None) == "변동없음"
    assert direction(None, "흑자 전환") == "흑자전환"
    assert direction(None, "-") is None


def test_label_values_keeps_group_for_follow_up_rows():
    kv = label_values(table_rows(SUPPLY))
    assert kv["계약기간 시작일"] == "2026-11-05" and kv["계약기간 종료일"] == "2028-06-30"
    assert kv["계약상대"] == "테스트물류(주)"


def test_decode_utf8_even_if_meta_says_euc_kr_and_cp949_fallback():
    text = _doc(["계약상대", "한국"])
    assert decode(text.encode("utf-8")) == text
    assert decode(text.encode("cp949")) == text


def test_fetch_document_reads_main_xml_from_zip(monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("20261102000001_00760.xml", "<html>첨부</html>")
        z.writestr("20261102000001.xml", SUPPLY)

    class Res:
        content = buf.getvalue()
        text = ""

    monkeypatch.setattr(dn.requests, "get", lambda *a, **k: Res())
    assert dn.fetch_document("20261102000001", "key") == SUPPLY


def test_fetch_document_error_payload(monkeypatch):
    class Res:
        content = b'{"status":"014","message":"\xed\x8c\x8c\xec\x9d\xbc\xec\x9d\xb4 \xec\xa1\xb4\xec\x9e\xac\xed\x95\x98\xec\xa7\x80 \xec\x95\x8a\xec\x8a\xb5\xeb\x8b\x88\xeb\x8b\xa4"}'
        text = '{"status":"014"}'

    monkeypatch.setattr(dn.requests, "get", lambda *a, **k: Res())
    with pytest.raises(RuntimeError):
        dn.fetch_document("x", "key")
