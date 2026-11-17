> 초안 (Claude 작성). 담당자 A 가 읽고 고쳐서 확정한다.

# tradingagents/run_report.py

- 한 줄 설명: TradingAgents 0.7.1 을 Claude 로 1회 돌려 분석 리포트(market·news)와 낙관·비관 토론만 한국어 JSON 으로 남기는 시험 스크립트.
- 입력: 티커, 분석 날짜, 루트 `.env` 의 `ANTHROPIC_API_KEY`·`DATABASE_URL`·`LLM_MONTHLY_LIMIT_USD`.
- 하는 일: 모델이 라이브러리 목록에 있는지 검사 → 이번 달 `llm_cost_log` 합계 + 1회 상한($2)이 월 한도를 넘으면 중단 → `propagate()` 실행, `final_state.keys()` 출력 → 리포트 2개와 bull/bear 만 추출, 결론 줄 삭제, 한국어 비율 50% 미만이면 haiku 로 번역 → 라이브러리 임시 폴더(결론 포함) 삭제.
- 출력: `tradingagents/logs/{TICKER}_{DATE}.json` (형식은 docs/tradingagents-trial.md). `--save` 면 모델별 비용을 `llm_cost_log` (module=tradingagents) 에 기록.
- 주의할 점: 매매 결론(Buy~Sell, 투자 계획, 트레이더 제안, 리스크 토론, 최종 결정)은 저장하지 않는다. 뉴스가 분석 날짜로 걸러지지 않아 탭 2 근거에 쓰지 않는다. 단가는 이 파일의 `PRICES` (worker llm_client 단가표에 이 두 모델이 없음). 반복 실행 금지 (월 한도).
- 테스트 순서: `--dry-run` (LLM 호출 없음) → 1회 실행 → JSON 의 `hangul_ratio`·`review_word_hits`·`cost_usd` 확인 → `--save` 로 기록됐는지 `llm_cost_log` 확인.
