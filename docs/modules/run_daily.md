> **초안 (Claude 작성, 2026-11-15).** 담당자 C가 읽고 고쳐서 확정한다.

# worker/run_daily.py

- **한 줄 설명**: 하루 파이프라인. 수집 → 계산 → 선별 점수 → 분류(Haiku) → 고르기 → 출제(Sonnet, 검증 포함) → pending 저장을 한 번에 돌린다.
- **입력**: 기준 거래일(`--date`, 없으면 오늘 이전 가장 최근 국내 거래일). `--skip-collect`(수집 건너뜀), `--no-llm`(선별 점수까지만, 비용 0), `--schedule`(APScheduler로 매일 08:00 KST). 실행은 `cd worker && python run_daily.py`.
- **하는 일**: ① 수집·계산: 국내 전 종목·지수 가격(`prices`), 1차 자료 DART·거시·8-K(`sources`, 8-K는 최근 겹침 결과의 미국 종목만), ETF 구성종목(`etf_holdings backfill <기준일>`: 기준일부터 빠진 날만 받아 평소엔 today 와 같고, 다시 돌리거나 전날 수집이 실패해도 채워진다. #87 리뷰), ETF 추세(`etf_trend --date --save`). ② 선별 점수: 기준일 직전 거래일 다음 날부터 기준일까지 나온 `raw_sources` 중 아직 카드가 되지 않은 자료(`card_sources`에 없는 것, #87 리뷰)마다 반응일(시각 있으면 `reaction_day`. 지수 자료는 KS11·KQ11이면 국내, IXIC·US500이면 미국 마감 시각으로 본다. DART처럼 없으면 당일·다음 거래일 중 큰 점수)의 거래량·수익률 점수를 `source_select`로 계산한다. 국내 종목은 그날 전 종목 순위(`cross_section_scores`), 지수·미국은 자기 과거 252일(`own_history_score`). ③ 1점 이상 중 상위 10건만 classify, `select`로 최대 3건, 각각 `compose`(검증·pending 저장).
- **출력**: 단계별 OK/ERR 출력, `logs/run_daily.jsonl`에 한 줄(기준일, 단계 결과, 만든 card_id). 실패한 단계가 하나라도 있으면 종료 코드 1.
- **주의할 점**: 같은 `--date`로 다시 돌려도 이미 카드가 된 자료는 다시 출제하지 않는다. 단계 하나가 실패해도(예외든 종료 코드 1이든) 나머지는 계속 돌린다. ETF 수집기가 1을 돌려주면 실패로 본다(B 요청 4). DART는 다음 거래일 점수까지 보려면 하루 늦게 다시 돌려야 한다(08:00 실행이면 당일 점수만 있음, 팀 확인 필요). 13F·겹침 계산은 분기마다라 여기에 넣지 않았다. 가격 카드(유형 1 채우기)는 A4(raw_sources 'price') 결정 전이라 아직 없다. `--schedule`은 프로세스가 떠 있는 동안만 돈다(배포 때 컨테이너로). APScheduler 의존성을 pyproject에 추가했다(3.x).
- **테스트**: `cd worker && python -m pytest tests/test_run_daily.py -q` (단계 성공·종료 코드·예외 기록, ETF 는 기준일부터 backfill, 이미 카드가 된 자료 제외, ETF 실패 후에도 계속 + 로그, `--no-llm`, 지수·미국 점수 손계산(거래량·수익률 최대 → 4점), 데이터 없는 날 0점, DART 두 날 중 큰 점수, 종목 없는 자료 0점, 월요일 → 금요일 기준일). **실제 DB·API로는 아직 돌리지 않았다.** 먼저 `python run_daily.py --skip-collect --no-llm --date <거래일>`로 점수만 확인하고, 그다음 `--no-llm` 없이 1번 돌려 비용을 본다.
