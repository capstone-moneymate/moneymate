> **초안 (Claude 작성, 2026-10-28).** 담당자 C가 읽고 고쳐서 확정한다.

# db/seeds/event_dates.csv (+ worker/scripts/build_event_dates.py)

- **한 줄 설명**: 차트 읽기의 "비슷했던 과거의 날" 후보표. 자동으로 찾지 않고 이 표에서 고른다 (기술확정안). 3주차 tools.py 의 `search_event_dates`가 읽는다.
- **입력**: FinanceDataReader 지수(KS11·IXIC) 2024-01-01~오늘, `collectors/macro_calendar.csv`(verified=Y, 이미 발표된 것만).
- **하는 일**: 하루 수익률 상·하위 4일(big_rise·big_drop), 비정상 거래량 상위 4일(volume_spike), 가장 긴 연속 상승 2구간의 마지막 날(consecutive_rise), FOMC·한은 금리 결정일(rate_decision)을 뽑는다. 숫자는 모두 코드가 계산한다.
- **출력**: 컬럼 `event_date, market, ticker, event_type, concept_id, value, note, source`.
- **주의할 점 (팀이 볼 것)**: 지금은 **후보**다. 팀이 note 를 보고 20~30줄로 줄인다. KS11 하루 +17.91%(2026-07-31), -12.06%(2026-03-04), +9.63%(2026-03-05), -9.99%(2026-06-23)는 pykrx KRX 지수(1001) 종가로 다시 계산해 같은 값임을 확인함(2026-10-28). rate_decision 줄의 concept_id 는 결정 전·후 금리로 코드가 채운다. 한은은 ECOS 기준금리(결정 당일부터 새 값), FOMC 는 FRED 목표 상단 DFEDTARU(결정 **다음 날**부터 새 값). 2026년 결과: 한은 동결 5·인상 2(7/16 2.50→2.75%, 8/27 2.75→3.00%), FOMC 동결 5·인상 1(9/16 3.75→4.00%). 다시 실행하면 파일을 덮어쓰므로 손으로 고친 뒤에는 다시 돌리지 않는다.
- **테스트**: `python -m pytest tests/test_build_event_dates.py -q` (앞쪽 기간은 계산에만 쓰고 상위 N개는 start 이후에서만 고르는지, start 전부터 이어진 연속 상승 길이). 처음엔 전체에서 고른 뒤 start 이전을 버려서 IXIC 급등 3줄·연속 상승 1줄로 모자랐던 것을 CodeRabbit 리뷰(PR #23)로 고침 → 41줄, 종류마다 정해진 개수(4·4·4·2). 생성: `cd worker && python scripts/build_event_dates.py` 후 줄 수와 note 를 눈으로 확인.
