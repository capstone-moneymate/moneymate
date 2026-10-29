"""환경변수와 상수. 공통 파일: A만 수정한다."""
import os
from pathlib import Path

from dotenv import load_dotenv

# 레포 루트의 .env 를 읽는다
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://moneymate:moneymate@localhost:5432/moneymate"
)
EDGAR_IDENTITY = os.environ.get("EDGAR_IDENTITY", "")
OPENFIGI_API_KEY = os.environ.get("OPENFIGI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MONTHLY_LIMIT_USD = float(os.environ.get("LLM_MONTHLY_LIMIT_USD", "10"))

# 큰손 4명 (filer_key -> 13F 제출 법인). 2026-10-10 확인, 근거는 docs/findings.md
# cik: 10자리 문자열. name: 13F 표지의 법인명 (화면 문구는 법인명 기준)
# ackman: 2026-06-30분부터 Pershing Square Inc.가 대신 보고. 11/14 3분기 공시 때 재확인
# extra_ciks: 같은 큰손의 다른 제출 법인. 수집·변화 계산 때 cik 와 합쳐 한 사람으로 본다.
#   ackman 2026-03-31분은 Pershing Square Capital Management(0001336528)가 11종목을 보고했고
#   0002026053 은 1종목(HHH)만 보고했다. 합치지 않으면 6/30분 14종목이 전부 "신규"로 잡힌다.
FILERS = {
    "buffett": {"cik": "0001067983", "name": "Berkshire Hathaway Inc"},
    "druckenmiller": {"cik": "0001536411", "name": "Duquesne Family Office LLC"},
    "thiel": {"cik": "0001562087", "name": "Thiel Macro LLC"},
    "ackman": {"cik": "0002026053", "name": "Pershing Square Inc.", "extra_ciks": ["0001336528"]},
}

# "늘림"으로 보는 최소 증가율 (0.05 = +5%). 2주차에 확정 (conventions.md P4)
# 13F "줄임"은 같은 크기의 감소(-5% 이하)로 본다 (overlap.py)
INCREASE_THRESHOLD = 0.05
# ETF 추세(분기 말 대비 1CU 수량 변화)를 늘림·줄림으로 보는 최소 변화율. 임시값, 3주차 실제 데이터로 확정
ETF_TREND_THRESHOLD = 0.05

# 방향 상수 (conventions.md)
DIRECTIONS = ("same", "diff", "none")
