> **초안 (Claude 작성, 2026-10-29).** 담당자 A가 읽고 고쳐서 확정한다.

# worker/collectors/filings_13f.py

- **한 줄 설명**: 큰손 4명의 분기 13F-HR을 SEC에서 받아 주식만 골라 `holdings_13f`에 저장하고, CUSIP→티커를 `cusip_map`에 캐시한다.
- **입력**: `.env`의 `EDGAR_IDENTITY`(필수), `OPENFIGI_API_KEY`(선택), `config.FILERS`(cik + extra_ciks), `--period`(분기 말, 없으면 버핏의 최근 분기), `--filer`, `--save`.
- **하는 일**: 지정한 분기와 그 직전 분기를 함께 받는다. 법인마다 13F-HR·13F-HR/A를 모아 정정 신고를 합치고(NEW HOLDINGS는 더하고 RESTATEMENT는 원본 대체), 주식만 남겨(P5) 같은 CUSIP을 합산한다(P14). 보유 없음 표시용 빈 줄(CUSIP `000000000`)은 뺀다. 티커는 cusip_map에 있으면 그 값, 없으면 OpenFIGI 값, OpenFIGI에 없으면 edgartools `Ticker` 순서로 정한다(#99: SEC 원본이 Lennar B주를 `LENB`로 적어 P1 형식 `LEN-B`와 달랐다. 다르면 화면에 출력). `--refresh-tickers`면 캐시를 무시하고 그 실행의 CUSIP을 다시 정한다.
- **출력**: `holdings_13f`에 (법인 CIK, 분기, CUSIP)마다 한 줄. 이미 있으면 수량·티커를 새 값으로 바꾼다(정정 신고 반영). `--save`가 없으면 화면 출력만.
- **정정 신고 버그 수정 (2026-11-19, #162)**: edgartools `get_filings`는 `amendments=True`가 기본이라 `form="13F-HR"`로 불러도 13F-HR/A가 섞여 온다. 예전에는 그 정정 신고를 원본으로 한 번, 13F-HR/A로 또 한 번 넣었다. 그래서 늦게 낸 NEW HOLDINGS가 대표 신고가 되어 원본 보유를 덮었다. 이제 `select_filings()`가 분기를 거르고 접수번호로 중복을 빼며, 원본/정정은 `Filing.form`으로만 가른다. `latest_period()`는 `amendments=False`로 원본만 본다. 실제로 걸린 경우는 에크먼 6/30분이다. 8/14 원본 14종목 뒤에 11/16 NEW HOLDINGS로 Pershing Square Inc.(71531U102) 184,289,699주가 공개되었다. 예전 코드로 다시 받으면 이 1종목만 남았다. 고친 뒤 2026-11-19에 6/30·9/30분을 다시 저장했다(249행, 티커 없음 0).
- **주의할 점**: 에크먼은 2026-03-31분을 0001336528(Pershing Square Capital Management)이 11종목, 0002026053이 HHH 1종목으로 나눠 냈다. 그래서 `extra_ciks`로 함께 받는다(행은 실제 제출 법인 CIK로 저장). 실제 확인 결과 HHH는 18,852,064 + 9,000,000 = 27,852,064주로 6/30분 합계와 맞았다. 틸 2026-03-31분은 보유가 없다는 빈 13F다. 평가액(Value) 단위 경고는 수량만 쓰므로 무시한다.
- **테스트**: `python -m pytest tests/test_filings_13f.py -q` (옵션·채권 제외, 같은 CUSIP 합산, 빈 줄 제외, 정정 신고 합치기, 같은 접수번호 한 번만 `select_filings`, 늦은 NEW HOLDINGS가 원본을 덮지 않음(원본 100·40 + 정정 50 = 3종목), 티커 정리, OpenFIGI 우선 `pick_ticker`). 2026-11-16 2분기 저장: CUSIP 154개 중 OpenFIGI 140·edgartools 14(해외 등록 G/N/H/Q/Y CUSIP은 OpenFIGI에 없음), 티커 없음 0. 2026-10-29 실제 호출(저장 없이): 6/30분 버핏 29, 드러켄밀러 86, 틸 8, 에크먼 14종목. DB 저장(`--save`)은 아직 실행 전.
