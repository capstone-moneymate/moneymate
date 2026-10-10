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
FILERS = {
    "buffett": {"cik": "0001067983", "name": "Berkshire Hathaway Inc"},
    "druckenmiller": {"cik": "0001536411", "name": "Duquesne Family Office LLC"},
    "thiel": {"cik": "0001562087", "name": "Thiel Macro LLC"},
    "ackman": {"cik": "0002026053", "name": "Pershing Square Inc."},
}

# "늘림"으로 보는 최소 증가율 (0.05 = +5%). 2주차에 확정 (conventions.md P4)
INCREASE_THRESHOLD = 0.05

# 방향 상수 (conventions.md)
DIRECTIONS = ("same", "diff", "none")
