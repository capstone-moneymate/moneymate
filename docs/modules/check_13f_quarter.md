> **초안 (Claude 작성, 2026-11-16).** 담당자 A가 읽고 고쳐서 확정한다.

# worker/scripts/check_13f_quarter.py

- **한 줄 설명**: 분기 13F 수집·변화 계산을 마친 뒤 `holdings_13f`를 읽어 큰손별로 이상한 값이 없는지 출력하는 점검 스크립트(읽기 전용, #99).
- **입력**: `--period`(분기 말), `--raw`(선택, SEC 원본을 다시 받아 옵션·채권 줄 수 확인. `EDGAR_IDENTITY` 필요).
- **하는 일**: 큰손 4명마다 ① 그 분기 행이 있는지(없으면 "공시 전이거나 수집 전") ② 보유 종목 수(exit 제외)와 직전 분기 대비 증감, 절반 이상 줄었거나 0이 되면 "급감" ③ change_type 개수와 빈 값·exit 규칙(shares=0, chg_pct=-1) 위반 ④ chg_pct 상위·하위 5개 ⑤ 제출 법인 CIK와 공시일 ⑥ 티커 없는 CUSIP. `--raw`면 원본 infotable 줄 수·옵션 줄·Shares 아닌 줄과 저장 대상 종목 수.
- **출력**: 화면 출력만. DB를 고치지 않는다.
- **주의할 점**: 급감 기준(50%)은 점검 표시용이고 "늘림" 임계값과 무관하다. 직전 분기가 빈 13F(틸 2026-03-31분)면 비교하지 않는다. new는 chg_pct가 NULL이라 상위·하위에 안 나온다. 같은 CUSIP을 여러 법인이 냈으면 수량을 합쳐 본다.
- **실행 순서** (분기 갱신, worker/ 에서):
  1. `python -m collectors.filings_13f --period 2026-09-30` (저장 없이 4명 제출 확인) → `--save`
  2. `python -m compute.holdings_change --period 2026-09-30` → `--save`
  3. `python scripts/check_13f_quarter.py --period 2026-09-30 --raw`
  4. ETF 스냅샷이 9/30 이후로 있을 때 `python -m compute.overlap --period 2026-09-30` → `--save`
- **테스트**: `python -m pytest tests/test_check_13f_quarter.py -q` (급감 경계 50%·0개·직전 0개, 상위·하위 정렬과 NULL 제외, 원본 줄 수가 수집기 필터 조건과 같은지). 2026-11-16 2분기 실데이터 실행: 버핏 29(원본 89줄), 드러켄밀러 86(옵션 9줄 제외), 틸 8, 에크먼 14(원본 15줄) — 수집기 문서 값과 같음.
