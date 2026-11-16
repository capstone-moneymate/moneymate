"""DART 공시 원문에서 핵심 숫자 뽑기 (C). sources.fetch_dart 가 raw_sources.numbers 를 채울 때 쓴다.

공시 이름만으로는 실적이 좋았는지 나빴는지, 계약이 회사에 얼마나 큰지 알 수 없어서
classify·proposals·compose 가 방향을 모른다 (2026-11-16 실데이터 확인). 그래서 정해진 서식의 표에서
숫자만 코드로 뽑아 넣는다. 원문 본문은 저장하지 않는다 (CLAUDE.md 9). 짧은 칸(계약상대, 목적 등)만 잘라 넣는다.

- 원문: DART OpenAPI document.xml (zip 안의 XML, 보통 EUC-KR). 표는 <TR> 안의 <TD>/<TH>/<TU>/<TE> 칸이다.
- 종류별로 뽑는 값 (키는 compose 프롬프트에 그대로 보이므로 한국어. 금액은 공시 단위 그대로 두고 '단위'를 함께 넣는다)
  - earnings (영업(잠정)실적): 실적기간, 단위, 매출액·영업이익·당기순이익의 당기·전년동기·증감률과 방향
  - earnings (매출액또는손익구조30%변동): 같은 항목을 직전 사업연도와 비교, 변동 주요원인
  - supply_contract: 계약금액(원), 최근매출액(원), 매출액대비(%), 계약상대, 공급지역, 계약기간
  - buyback (자기주식취득결정): 취득예정주식(주), 취득예정금액(원), 취득기간, 취득목적
  - buyback (주식소각결정): 소각주식(주), 발행주식총수(주), 발행주식대비(%)(코드 계산), 소각예정금액(원), 소각예정일
  - capex: 투자금액(원), 자기자본(원), 자기자본대비(%), 투자대상, 투자목적, 투자기간
- 자회사 주요경영사항 공시면 '자회사' 에 자회사 이름을 넣는다 (숫자가 상장사 본인 것이 아니다).
- 방향(증가·감소·흑자전환·적자전환·적자지속)은 증감률 부호와 공시의 흑자적자전환 칸으로 코드가 정한다.

실행 (확인용): cd worker && python collectors/dart_numbers.py 20261102800240 earnings
"""
import html
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # worker/ 를 import 경로에

import config  # noqa: E402,F401  .env 를 읽는다

DART_DOC_URL = "https://opendart.fss.or.kr/api/document.xml"
TEXT_MAX = 80  # 글 칸(계약상대·목적·원인)은 이 길이로 자른다. 본문 저장 금지 (CLAUDE.md 9)
EARNING_ITEMS = ("매출액", "영업이익", "당기순이익")
TURNS = ("흑자전환", "적자전환", "적자지속")


# ------------------------------------------------------------------
# 원문 받기·표 읽기
# ------------------------------------------------------------------
def fetch_document(rcept_no: str, api_key: str | None = None) -> str:
    """document.xml zip → 본문 XML 문자열. zip 이 아니면(오류 응답) RuntimeError."""
    api_key = api_key or os.getenv("DART_API_KEY")
    res = requests.get(DART_DOC_URL, params={"crtfc_key": api_key, "rcept_no": rcept_no}, timeout=30)
    if not res.content.startswith(b"PK"):
        raise RuntimeError(f"DART 원문을 받지 못했어요 ({rcept_no}): {res.text[:120]}")
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        names = sorted(z.namelist(), key=lambda n: (n != f"{rcept_no}.xml", -z.getinfo(n).file_size))
        return decode(z.read(names[0]))


def decode(raw: bytes) -> str:
    """UTF-8 로 먼저 읽고, 안 되면 cp949(euc-kr). meta 에 charset=euc-kr 이라고 적혀 있어도
    API 가 주는 파일은 UTF-8 인 경우가 있다 (2026-11-16 실제 공시로 확인). 그래서 선언을 믿지 않는다."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp949", errors="replace")


def table_rows(text: str) -> list[list[str]]:
    """표의 줄마다 칸 글자 목록. 태그를 지우고 공백을 하나로 줄인다. 빈 줄은 뺀다."""
    rows = []
    for tr in re.findall(r"<TR[^>]*>(.*?)</TR>", text, re.S | re.I):
        cells = re.findall(r"<T[DHUE][^>]*>(.*?)</T[DHUE]>", tr, re.S | re.I)
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip() for c in cells]
        if any(cells):
            rows.append(cells)
    return rows


# ------------------------------------------------------------------
# 값 정리
# ------------------------------------------------------------------
def num(s: str | None) -> float | int | None:
    """'83,098,217,738' → 83098217738, '-4.2' → -4.2, '△12' → -12, '-'·빈칸 → None."""
    if s is None:
        return None
    t = s.replace(",", "").replace(" ", "").replace("△", "-").replace("▲", "-")
    if re.fullmatch(r"\(\d+(\.\d+)?\)", t):  # (123) 은 음수
        t = "-" + t[1:-1]
    if not re.fullmatch(r"-?\d+(\.\d+)?", t):
        return None
    v = float(t)
    return int(v) if v.is_integer() and "." not in t else v


def iso_date(s: str | None) -> str | None:
    """'2026-11-03' 또는 '2026년 11월 03일' → '2026-11-03'. 아니면 None."""
    if not s:
        return None
    m = re.search(r"(\d{4})\s*[-.년]\s*(\d{1,2})\s*[-.월]\s*(\d{1,2})", s)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


def short(s: str | None) -> str | None:
    if not s or s.strip() in ("-", "－"):
        return None
    s = s.strip()
    return s if len(s) <= TEXT_MAX else s[:TEXT_MAX] + "…"


def unit_of(text: str) -> str | None:
    """'단위 : 억원, %' · '(단위:천원)' → '억원' · '천원'."""
    m = re.search(r"단위\s*[:：]\s*([가-힣]*원)", text)
    return m.group(1) if m else None


def _label(s: str) -> str:
    """'2. 계약내역' → '계약내역', '- 체결계약명' → '체결계약명', 안쪽 공백 제거."""
    s = re.sub(r"^\s*(\d+\.|-)\s*", "", s)
    return re.sub(r"\s+", "", s)


def label_values(rows: list[list[str]]) -> dict[str, str]:
    """'라벨 | 값' 또는 '묶음 | 라벨 | 값' 줄을 {라벨: 값} 으로. 묶음이 있으면 '묶음 라벨' 키도 넣는다.

    '종료일 | 값' 처럼 묶음 없이 다음 줄에 이어지는 칸은 바로 앞 묶음(계약기간 등)을 쓴다.
    '3. 계약상대 | 값' 처럼 번호로 시작하는 두 칸 줄은 새 항목이라 묶음을 비운다. 같은 키는 처음 값만 남긴다.
    """
    kv: dict[str, str] = {}
    group = ""
    for c in rows:
        if len(c) >= 3:
            group, sub, val = _label(c[0]), _label(c[1]), c[2]
        elif len(c) == 2:
            if re.match(r"^\s*\d+\.", c[0]):
                group = ""
            sub, val = _label(c[0]), c[1]
        else:
            continue
        for k in (sub, f"{group} {sub}" if group else None):
            if k and k not in kv:
                kv[k] = val
    return kv


def direction(pct: float | None, turn: str | None) -> str | None:
    """흑자적자전환 칸이 있으면 그 말, 없으면 증감률 부호로 증가·감소·변동없음."""
    if turn:
        for t in TURNS:
            if t in turn.replace(" ", ""):
                return t
    if pct is None:
        return None
    return "증가" if pct > 0 else "감소" if pct < 0 else "변동없음"


def _put(out: dict, key: str, value) -> None:
    if value is not None:
        out[key] = value


# ------------------------------------------------------------------
# 종류별
# ------------------------------------------------------------------
def earnings_numbers(rows: list[list[str]]) -> dict:
    """영업(잠정)실적(공정공시). 당해실적 줄: [항목, '당해실적', 당기, 전기, 전기대비%, 전기전환, 전년동기, 전년동기대비%, 전년동기전환]."""
    out: dict = {}
    for cells in rows:
        if cells and cells[0] == "당기실적" and len(cells) >= 4 and iso_date(cells[1]):
            _put(out, "실적기간", f"{iso_date(cells[1])}~{iso_date(cells[-1])}")
        if "단위" not in out:
            _put(out, "단위", unit_of(" ".join(cells)))
        if len(cells) >= 9 and cells[1].replace(" ", "") == "당해실적":
            item = cells[0].replace(" ", "")
            if item not in EARNING_ITEMS:
                continue
            cur, prev_q, qoq, qoq_turn, prev_y, yoy, yoy_turn = (cells[2], cells[3], cells[4], cells[5],
                                                                 cells[6], cells[7], cells[8])
            if num(cur) is None:
                continue
            _put(out, item, num(cur))
            _put(out, f"{item} 전년동기", num(prev_y))
            _put(out, f"{item} 전년동기대비(%)", num(yoy))
            _put(out, f"{item} 전년동기대비 방향", direction(num(yoy), short(yoy_turn)))
            _put(out, f"{item} 전기대비(%)", num(qoq))
            _put(out, f"{item} 전기대비 방향", direction(num(qoq), short(qoq_turn)))
    if not any(k in out for k in EARNING_ITEMS):  # 값이 모두 '-' 인 공시 (예: 월별 실적 미기재)
        return {}
    return out


def change30_numbers(rows: list[list[str]]) -> dict:
    """매출액또는손익구조30%(대규모법인은15%)이상변동. 항목 줄: ['- 매출액', 당해, 직전, 증감금액, 증감비율, 흑자적자]."""
    out: dict = {}
    for cells in rows:
        joined = " ".join(cells)
        # '- 시작일 | 당해 | 직전' / '- 종료일 | ...'. 직전사업연도가 직전 분기인 공시도 있어서 기간을 같이 넣는다
        if cells and _label(cells[0]) in ("시작일", "종료일") and len(cells) >= 3:
            key = "시작" if _label(cells[0]) == "시작일" else "종료"
            out[f"_당해{key}"], out[f"_직전{key}"] = iso_date(cells[1]), iso_date(cells[2])
        if "변동내용" in joined:
            _put(out, "단위", unit_of(joined))
        item = _label(cells[0]) if cells else ""
        if item in EARNING_ITEMS and len(cells) >= 6 and num(cells[1]) is not None:
            _put(out, item, num(cells[1]))
            _put(out, f"{item} 직전사업연도", num(cells[2]))
            _put(out, f"{item} 증감비율(%)", num(cells[4]))
            _put(out, f"{item} 방향", direction(num(cells[4]), short(cells[5])))
        if "주요원인" in joined and len(cells) >= 2:
            _put(out, "변동 주요원인", short(cells[-1]))
    for side in ("당해", "직전"):
        start, end = out.pop(f"_{side}시작", None), out.pop(f"_{side}종료", None)
        if start and end:
            out[f"{side}기간"] = f"{start}~{end}"
    return out if any(k in out for k in EARNING_ITEMS) else {}


def supply_numbers(kv: dict[str, str]) -> dict:
    out: dict = {}
    _put(out, "체결계약명", short(kv.get("체결계약명")))
    _put(out, "계약금액(원)", num(kv.get("계약금액(원)")))
    _put(out, "최근매출액(원)", num(kv.get("최근매출액(원)")))
    _put(out, "매출액대비(%)", num(kv.get("매출액대비(%)")))
    _put(out, "계약상대", short(kv.get("계약상대")))
    _put(out, "공급지역", short(kv.get("판매ㆍ공급지역") or kv.get("판매·공급지역")))
    _put(out, "계약 시작일", iso_date(kv.get("계약기간 시작일")))
    _put(out, "계약 종료일", iso_date(kv.get("계약기간 종료일")))
    return out


def buyback_numbers(kv: dict[str, str]) -> dict:
    out: dict = {}
    _put(out, "취득예정주식(주)", num(kv.get("취득예정주식(주) 보통주식")))
    _put(out, "취득예정금액(원)", num(kv.get("취득예정금액(원) 보통주식")))
    _put(out, "취득 시작일", iso_date(kv.get("취득예상기간 시작일")))
    _put(out, "취득 종료일", iso_date(kv.get("취득예상기간 종료일")))
    _put(out, "취득목적", short(kv.get("취득목적")))
    _put(out, "취득방법", short(kv.get("취득방법")))
    return out


def cancel_numbers(kv: dict[str, str]) -> dict:
    """보통주 소각이면 '소각주식(주)'·'발행주식대비(%)', 종류주식(우선주 등)만 소각하면 '종류주식' 이 붙은 키 (한화 11/12 공시)."""
    out: dict = {}
    for kind, prefix in (("보통주식", ""), ("종류주식", "종류주식 ")):
        shares = num(kv.get(f"소각할주식의종류와수 {kind}(주)"))
        total = num(kv.get(f"발행주식총수 {kind}(주)"))
        if not shares:
            continue
        out[f"{prefix}소각주식(주)"] = shares
        _put(out, f"{prefix}발행주식총수(주)", total)
        if total:
            out[f"{prefix}발행주식대비(%)"] = round(shares / total * 100, 2)
    _put(out, "소각예정금액(원)", num(kv.get("소각예정금액(원)")))
    _put(out, "소각예정일", iso_date(kv.get("소각예정일")))
    _put(out, "취득방법", short(kv.get("소각할주식의취득방법")))
    return out


def capex_numbers(kv: dict[str, str]) -> dict:
    out: dict = {}
    _put(out, "투자대상", short(kv.get("투자대상")))
    _put(out, "투자금액(원)", num(kv.get("투자금액(원)")))
    _put(out, "자기자본(원)", num(kv.get("자기자본(원)")))
    _put(out, "자기자본대비(%)", num(kv.get("자기자본대비(%)")))
    _put(out, "투자목적", short(kv.get("투자목적")))
    _put(out, "투자 시작일", iso_date(kv.get("투자기간 시작일")))
    _put(out, "투자 종료일", iso_date(kv.get("투자기간 종료일")))
    return out


def subsidiary(rows: list[list[str]]) -> str | None:
    """'자회사인 | 효성투자개발(주) | 의 주요경영사항신고' 줄이 있으면 자회사 이름."""
    for cells in rows[:5]:
        if len(cells) >= 2 and cells[0].replace(" ", "") == "자회사인":
            return short(cells[1])
    return None


def parse_numbers(category: str, title: str, text: str) -> dict:
    """공시 종류(category)와 제목으로 서식을 골라 숫자 dict. 서식이 안 맞으면 빈 dict."""
    rows = table_rows(text)
    name = title.replace(" ", "")
    if category == "earnings":
        out = change30_numbers(rows) if "손익구조" in name else earnings_numbers(rows)
    elif category == "supply_contract":
        out = supply_numbers(label_values(rows))
    elif category == "buyback":
        out = cancel_numbers(label_values(rows)) if "소각" in name else buyback_numbers(label_values(rows))
    elif category == "capex":
        out = capex_numbers(label_values(rows))
    else:
        return {}
    if out:
        _put(out, "자회사", subsidiary(rows))
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    rcept_no, category = argv[0], argv[1]
    title = " ".join(argv[2:])
    print(json.dumps(parse_numbers(category, title, fetch_document(rcept_no)), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
