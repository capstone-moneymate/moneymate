> **초안 (Claude 작성, 2026-11-02).** 담당자 B가 읽고 고쳐서 확정한다.

# worker/compute/indicators.py

- **한 줄 설명**: RSI·기간 수익률·거래량 배수·거래량 상위일을 계산하는 순수 함수 모음. 출제 도구(C의 tools.py)와 차트 읽기 화면이 같은 함수를 써서 정답과 화면 숫자가 어긋나지 않게 한다.
- **입력**: 종가 목록, 거래량 목록, `market_date`·`volume` 컬럼 표. DB는 부르지 않는다(가격은 부르는 쪽이 `prices`에서 읽어 넘긴다).
- **하는 일**: `wilder_rsi`(마지막 날 RSI), `rsi_series`(날짜마다의 RSI, 차트 선용, 앞 period개는 None), `pct_return`(수익률 %), `volume_ratio`(마지막 날 거래량 ÷ 앞 날들 평균), `top_volume_days`(거래량 큰 순, 같으면 이른 날 먼저). 모두 소수 2자리.
- **출력**: 숫자 또는 `{"date", "volume"}` 목록. 입력이 모자라면 `ValueError`.
- **주의할 점**: C의 tools.py(agent-tools-42)에 있던 계산을 그대로 옮겼다(C와 합의: 계산은 여기, tools.py는 가져다 씀). tools.py를 바꿀 때 `ValueError`를 `ToolError`로 바꿔 에이전트에게 보여 줘야 한다. RSI는 Wilder(1978) 원래 정의(첫 평균은 단순 평균, 그다음 평활)다. 기술확정안의 pandas-ta-classic `rsi()`는 같은 평활을 ewm으로 근사해 시작값만 다르다. 무작위 가격 300개씩 비교하면 소수 2자리 기준 최대 차이가 15일 14.21, 30일 6.67, 60일 0.89, 120일 0.02, 252일 0.00이다. 출제 도구는 252거래일을 넣으므로 결과가 같다. 차트에 짧은 기간만 넣으면 앞부분 RSI가 다른 사이트 값과 다를 수 있다. pandas-ta-classic은 의존성에 넣지 않았다.
- **테스트**: `cd worker && python -m pytest tests/test_indicators.py -q` (RSI 손계산 90·83.33, 손실 0이면 100, 데이터 부족, 일별 RSI 손계산과 매일 마지막 값과 일치, 수익률, 거래량 배수, 상위일 동점). C의 test_tools.py 계산 테스트와 같은 숫자다. 2026-11-02 C의 tools.py 함수와 무작위 입력 1,800가지를 비교해 모두 같음.
