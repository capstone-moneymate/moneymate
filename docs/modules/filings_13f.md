> **초안 (Claude 작성, 2026-10-29).** 담당자 A가 읽고 고쳐서 확정한다.

# worker/collectors/filings_13f.py

- **한 줄 설명**: 큰손 4명의 분기 13F-HR을 SEC에서 받아 주식만 골라 `holdings_13f`에 저장하고, CUSIP→티커를 `cusip_map`에 캐시한다.
- **입력**: `.env`의 `EDGAR_IDENTITY`(필수), `OPENFIGI_API_KEY`(선택), `config.FILERS`(cik + extra_ciks), `--period`(분기 말, 없으면 버핏의 최근 분기), `--filer`, `--save`.
- **하는 일**: 지정한 분기와 그 직전 분기를 함께 받는다. 법인마다 13F-HR·13F-HR/A를 모아 정정 신고를 합치고(NEW HOLDINGS는 더하고 RESTATEMENT는 원본 대체), 주식만 남겨(P5) 같은 CUSIP을 합산한다(P14). 보유 없음 표시용 빈 줄(CUSIP `000000000`)은 뺀다. 티커는 cusip_map → edgartools `Ticker` → OpenFIGI 순서로 찾는다.
- **출력**: `holdings_13f`에 (법인 CIK, 분기, CUSIP)마다 한 줄. 이미 있으면 수량·티커를 새 값으로 바꾼다(정정 신고 반영). `--save`가 없으면 화면 출력만.
- **주의할 점**: 에크먼은 2026-03-31분을 0001336528(Pershing Square Capital Management)이 11종목, 0002026053이 HHH 1종목으로 나눠 냈다. 그래서 `extra_ciks`로 함께 받는다(행은 실제 제출 법인 CIK로 저장). 실제 확인 결과 HHH는 18,852,064 + 9,000,000 = 27,852,064주로 6/30분 합계와 맞았다. 틸 2026-03-31분은 보유가 없다는 빈 13F다. 평가액(Value) 단위 경고는 수량만 쓰므로 무시한다.
- **테스트**: `python -m pytest tests/test_filings_13f.py -q` (옵션·채권 제외, 같은 CUSIP 합산, 빈 줄 제외, 정정 신고 합치기, 티커 정리). 2026-10-29 실제 호출(저장 없이): 6/30분 버핏 29, 드러켄밀러 86, 틸 8, 에크먼 14종목. DB 저장(`--save`)은 아직 실행 전.
