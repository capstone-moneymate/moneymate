> **초안 (Claude 작성, 2026-11-01).** 담당자 C가 읽고 고쳐서 확정한다.

# worker/generate/tools.py

- **한 줄 설명**: 출제 에이전트(compose)가 tool use로 부르는 도구 7개. 숫자·경로·검증은 코드가 계산하고 Claude는 결과로 문장만 쓴다.
- **입력**: Claude의 `tool_use` 블록(이름·입력)과 `ToolContext`(카드의 1차 자료 원문, 로그용 자료 키). 원문은 에이전트가 아니라 compose가 넣어서, 근거 인용 검증을 에이전트가 바꿀 수 없다.
- **도구**: `calc_rsi`(Wilder, 첫 평균은 단순 평균) · `calc_return`(두 날짜 종가 수익률 %) · `volume_stats`(그날 거래량 ÷ 직전 252거래일 평균, 그날까지 최근 N거래일 중 거래량 상위 3일) · `find_concept_path`(B의 graph.py, end가 null이면 닿는 모든 결과) · `search_event_dates`(db/seeds/event_dates.csv, 최신순 최대 10개) · `validate_causal_order`(B의 validators.py) · `validate_chart_answer`(차트 문제에 쓴 수익률·거래량 배수·거래량 최대일·RSI를 다시 계산해 비교, 허용 오차 0.01).
- **원시 가격 도구는 두지 않는다**: 종가·거래량 표를 주면 에이전트가 숫자를 직접 계산할 수 있어서, 계산된 값만 돌려준다.
- **출력**: `run_tool(name, args, ctx) → (JSON 문자열, is_error)`. 그대로 `tool_result`의 content·is_error에 넣는다. 입력이 틀리거나 데이터가 없으면 예외 대신 오류 문장을 돌려줘서 에이전트가 고치게 한다. 검증 실패는 오류가 아니라 결과(`passed: false` + 이유)다.
- **로그**: 도구 호출마다 `logs/tool_calls.jsonl`에 1줄(시각·도구·자료 키·입력·성공 여부·오류·ms).
- **주의할 점**: 도구 정의는 모두 `strict: true`(스키마에 맞는 입력만 옴). 가격은 `prices` 테이블에서만 읽어서 run_daily가 미리 수집해 둬야 한다. RSI 정의는 B의 indicators.py와 같아야 한다(팀 확인). 252거래일이 다 안 차면 `avg_days`가 252보다 작게 나온다. 개념 사전은 B의 graph·validators와 같이 db/seeds csv에서 읽는다.
- **테스트**: `cd worker && python -m pytest tests/test_tools.py -q` (RSI 손계산 2개·손실 0·데이터 부족, 수익률·거래량 배수·상위일 동점, 가짜 가격표로 도구 실행, 차트 정답 검증 통과·실패·잘못된 입력, 오류가 로그에 남는지, rate_hold → growth_valuation 경로·방향, 닿는 모든 결과, 이벤트 날짜 최신순, 인과 순서 검증 통과·방향 오류, 스키마 strict).
