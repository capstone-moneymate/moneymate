"""티커 정규화 (conventions.md P1). 저장 직전에 항상 이 함수를 거친다."""
import re


def normalize_us_ticker(raw: str) -> str:
    """'brk.b ' -> 'BRK-B'. 대문자, 공백 제거, 클래스주 구분은 하이픈."""
    t = raw.strip().upper().replace(".", "-").replace("/", "-")
    t = re.sub(r"\s+", "", t)
    if not re.fullmatch(r"[A-Z]{1,5}(-[A-Z])?", t):
        raise ValueError(f"미국 티커 형식이 아님: {raw!r}")
    return t


def normalize_kr_code(raw: str | int) -> str:
    """426030 / '426030' / '5930' -> 6자리 문자열 ('005930').

    영문 대문자가 섞인 코드('0015B0' ETF, '00104K' 우선주)도 받는다.
    앞자리 0 채우기는 숫자만 있을 때만 한다. 엑셀·int 변환으로 0이 빠지는 건 숫자 코드뿐이라서.
    """
    s = str(raw).strip().upper()
    if s.isdigit() and len(s) <= 6:
        return s.zfill(6)
    if re.fullmatch(r"[0-9A-Z]{6}", s) and re.search(r"[0-9]", s):
        return s
    raise ValueError(f"한국 종목 코드 형식이 아님: {raw!r}")
