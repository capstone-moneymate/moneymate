> **초안 (Claude 작성, 2026-11-01).** 담당자 B가 읽고 고쳐서 확정한다.

# worker/collectors/etf_holdings.py

- **한 줄 설명**: 액티브 ETF 2개(TIME 426030, KoAct 0015B0)의 구성종목과 1CU 기준 수량을 pykrx로 받아 `holdings_etf`에 쓴다.
- **입력**: `.env` 의 `KRX_ID`·`KRX_PW`(pykrx 로그인), 날짜. `today`는 최근 거래일, `backfill 2026-09-30`은 그날부터 최근 거래일까지 DB에 없는 날만, `show 날짜`는 저장 없이 출력만.
- **하는 일**: 원화현금 `010010`·설정현금액 `H00000`·선물(코드 6자리 아님)을 빼고 주식만 남긴다(P16). 같은 코드 두 줄은 합치고 수량 0은 뺀다. 수량은 Decimal로 바꿔 KoAct 소수(99.88)를 오차 없이 넣는다. 저장 전에 직전 스냅샷과 비교해, 겹치는 종목이 5개 이상이고 전부 같은 비율(0.5% 안)로 변했으면 설정 단위 변경 경고를 출력한다(저장은 그대로 함). 저장 후 `cusip_map`의 CUSIP 2~7번째 글자로 `ticker`를 채운다.
- **출력**: `holdings_etf` 행 (`etf_code`, `snapshot_date`, `raw_code`, `stock_name`, `shares`, `source='pykrx'`). `trend_chg_pct`·`day_chg_pct`·`trend_base_date`는 비워 두고 etf_trend.py가 채운다.
- **주의할 점**: 한 번 받은 날짜는 덮어쓰지 않는다(P6, `ON CONFLICT DO NOTHING`). ticker는 한 raw_code에 티커가 둘 이상 나오면 채우지 않고, 13F에 없는 종목은 NULL로 남는다. 거래일 달력은 C의 `prices.kr_trading_days`(KS11 날짜)를 쓴다. KRX가 연결을 끊는 일이 있어 3번 재시도, 백필은 하루마다 1초 쉰다. 매일 자동 실행은 C의 run_daily.py(6주차)에 넣기 전까지 직접 돌린다.
- **테스트**: `cd worker && python -m pytest tests/test_etf_holdings.py -q` (현금·선물 제외, 소수 수량 Decimal, 중복 합침·0 제외, 설정 단위 2배 감지·반올림 허용·일반 매매는 경고 없음·겹치는 종목 부족). 2026-11-01 B의 PC에서 `show` 실행: 10/30 TIME 주식 39종목, KoAct 52종목 받아짐. 이어서 `backfill 2026-09-30`으로 9/30~10/30 거래일 21일 × 2개 ETF를 DB에 저장함(설정 단위 경고 없음). 9/30 줄 수는 findings.md B칸 확인 결과(TIME 44줄·KoAct 46줄에서 현금·선물 제외)와 맞음. 13F를 아직 안 받은 DB라 ticker 채움은 0줄.
