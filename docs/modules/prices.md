> **초안 (Claude 작성, 2026-10-28).** 담당자 C가 읽고 고쳐서 확정한다.

# worker/collectors/prices.py

- **한 줄 설명**: 국내 전 종목 하루치(pykrx)와 지수 4개·미국 종목(FinanceDataReader → 실패 시 yfinance)의 가격·거래량을 `prices` 테이블에 쓴다.
- **입력**: `.env` 의 `KRX_ID`·`KRX_PW`(pykrx 로그인), 날짜. 지수 키는 `KS11`·`KQ11`·`IXIC`·`US500`(탭1 홈 4개).
- **하는 일**: `today`는 최근 거래일 국내 전 종목 + 지수, `backfill 253`은 국내 253거래일(선별 점수의 252일 평균 + 당일), `us NVDA 시작일`은 미국 종목 1개. 같은 (ticker, market_date)는 새 값으로 덮어쓴다.
- **출력**: `prices` 행. `fetch_kr_daily`는 저장하지 않는 `chg_pct`(KRX 공식 등락률, 소수)도 돌려줘서 `source_select.cross_section_scores`가 그날 수익률 순위에 쓴다. `load_volume_history`는 종목별 직전 252거래일 거래량을 읽는다.
- **주의할 점**: 거래량 0(거래정지)은 저장하지 않는다. KRX 신규 코드(예: 우선주 `00104K`)에 영문이 섞여 `normalize_kr_code`가 거부해서 `kr_code()`로 임시 처리 중 (A에게 영문 허용 요청, B의 `0015B0`과 같은 건). KRX가 연속 요청 중 연결을 끊어서 3번 재시도 + 백필은 하루마다 1초 쉰다. 미국장 날짜는 미국 거래일 그대로 저장한다 (conventions.md).
- **테스트**: 네트워크 함수라 pytest 없음. 2026-10-28 Claude가 C의 PC에서 DB 없이 변환만 확인: 10/27 국내 2,729종목, 지수 4개, NVDA 모두 받아짐. DB 저장(`python collectors/prices.py today`)은 Docker를 켠 뒤 C가 확인한다.
