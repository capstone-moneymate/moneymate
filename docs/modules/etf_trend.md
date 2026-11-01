> **초안 (Claude 작성, 2026-11-01).** 담당자 B가 읽고 고쳐서 확정한다.

# worker/compute/etf_trend.py

- **한 줄 설명**: `holdings_etf`의 일일 스냅샷으로 종목별 분기 말 대비 추세(`trend_chg_pct`)와 전 거래일 대비 변화(`day_chg_pct`)를 계산해 같은 행에 채운다. 탭 2 화면 표시용이다.
- **입력**: `holdings_etf` 스냅샷(etf_holdings.py가 쌓음). `--date 날짜`면 그날만, 없으면 모든 스냅샷 날짜. `--save`를 붙여야 DB에 반영한다(A의 compute 모듈과 같은 방식).
- **하는 일**: 변화율은 P2 식 `(지금 - 이전) / 이전`, 이전이 없거나 0이면 NULL이다. overlap.py `etf_change`와 같은 식·같은 반올림(소수 6자리)이다. 추세 기준일은 그 스냅샷이 속한 분기의 분기 말, 그날 스냅샷이 없으면 그 이후 첫 스냅샷이다(P15, overlap.py가 ETF 기준 스냅샷을 고르는 방식과 같음). 전일은 바로 앞 스냅샷 날짜다.
- **출력**: `trend_chg_pct`, `day_chg_pct`, `trend_base_date` 컬럼. 스냅샷 수량·코드는 건드리지 않는다(P6). 실행하면 ETF별 최신 날짜의 늘림·줄임·변화 작음·신규 개수를 출력한다(임계값은 `config.ETF_TREND_THRESHOLD`).
- **주의할 점**: 겹침 판정은 이 값을 쓰지 않고 overlap.py가 13F 분기 말 기준으로 따로 계산한다(overlap.md 질문에 대한 B의 답). 편출 종목(기준일엔 있고 최신엔 없음)은 최신 날짜에 행이 없어 값을 채우지 않는다. overlap.py는 이 경우를 "줄임"으로 따로 처리한다. 화면에 편출을 보여 줘야 하면 그때 정한다. 12/31은 KRX 휴장이라 4분기 기준일은 다음 해 첫 스냅샷이 된다. 수집을 빠뜨린 날이 있으면 전일 대비는 그 앞 스냅샷과 비교된다.
- **테스트**: `cd worker && python -m pytest tests/test_etf_trend.py -q` (변화율 손계산·NULL, 기준일=분기 말 스냅샷·수집 시작일 대체·다음 분기 초기화, 휴장일 건너뛴 전일, 추세·전일 함께 계산·신규 NULL·편출 제외, 요약 개수). 2026-11-01 B의 DB(9/30~10/30)로 실행해 10/30 NVIDIA·Apple 두 ETF 값을 SQL로 따로 계산한 값과 대조함(TIME NVIDIA 226 → 238 = +0.053097, KoAct Apple은 9/30에 없어서 추세 NULL).
