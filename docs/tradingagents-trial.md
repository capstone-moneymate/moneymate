# TradingAgents 1주 시험 (#102)

탭 1 해설 재료(분석 리포트, 낙관·비관 토론)로 쓸 수 있는지 본다. 탭 2 근거에는 쓰지 않는다 (기술확정안: 뉴스가 분석 날짜로 걸러지지 않음).

## 환경 (worker 와 분리)

```bash
cd tradingagents
py -3.12 -m venv .venv                        # macOS/Linux: python3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python.exe run_report.py --dry-run              # LLM 호출 없이 모델 목록·남은 월 한도 확인
.venv/Scripts/python.exe run_report.py NVDA 2026-11-16 --save # 1회 실행 + llm_cost_log 기록
```

- 키: 루트 `.env` 의 `ANTHROPIC_API_KEY` 를 읽는다 (새 키 이름 없음). 출력·저장하지 않는다.
- 쓰기 경로: 라이브러리의 `TRADINGAGENTS_RESULTS_DIR`·`TRADINGAGENTS_CACHE_DIR`·`TRADINGAGENTS_MEMORY_LOG_PATH` 를 `tradingagents/logs/_lib_tmp/` 로 돌리고 실행 뒤 지운다. 라이브러리는 여기에 매매 결론이 든 전체 상태와 메모리 로그를 쓰기 때문이다.
- 결과: `tradingagents/logs/{TICKER}_{DATE}.json` 하나만 남는다 (`logs/` 는 gitignore).
- 한도: 실행 전 이번 달 `llm_cost_log` 합계 + 1회 상한 추정 $2 가 `LLM_MONTHLY_LIMIT_USD` 를 넘으면 실행하지 않는다. `--save` 면 모델별 비용을 `module='tradingagents'` 로 기록해 C 의 출제·A 의 채점과 같은 한도에 잡힌다.
- 데이터: 시세·지표·뉴스는 yfinance (키 없음). 뉴스 분석가의 거시지표 도구(FRED)는 `FRED_API_KEY` 가 없어 "사용 불가"로 넘어간다 (멈추지 않음).

## 통과 기준 표

| 시험 항목 | 통과 기준 | 설정 | 결과 |
| :--- | :--- | :--- | :--- |
| 연결 | Claude 로 분석 1회 완주 | `llm_provider="anthropic"`, quick `claude-haiku-4-5`, deep `claude-sonnet-5` (설치본 모델 목록에서 확인) | **통과**: NVDA 2026-11-16 1회 완주 (종료 코드 0) |
| 비용·시간 | 종목 1개를 월 한도 안에서 매일 돌릴 수 있음 (30회 × 1회 비용 ≤ 남는 한도) | `max_debate_rounds=1`, `max_risk_discuss_rounds=1`, 분석가 market·news | **불통과**: 1회 $0.438, 15분 11초(910.7초). 30회 = $13.14 > 월 한도 $10 (C 출제·A 채점과 같은 한도). 한도를 이것만 써도 월 22회 |
| 한국어 | 해설 재료로 쓸 만한 품질 | `output_language="Korean"` | **조건부**: 한글 비율 0.77~0.87, 번역 0회. 오역·오타 있음 (아래 "실행 결과") |
| 저장 | 리포트 + 낙관·비관 토론만 JSON, 매매 결론 제외 | `final_state.keys()` 출력 후 아래 필드만 추출 | **형식 통과, 내용 불통과**: 결론 줄 필터 수정 후 `Rating` 0건. 그러나 토론 본문 자체가 매수·매도 권유·목표가·수익률이다 (아래) |
| 버전 | 설치본으로 확정 | `pip show`, `pyproject.toml` | **통과**: 0.7.1, 커밋 `3e44faa` ([VERSION.md](../tradingagents/VERSION.md)) |

## 실행 결과 (2026-11-16, NVDA, 1회)

결과 파일: `tradingagents/logs/NVDA_2026-11-16.json` (gitignore, 로컬에만). `llm_cost_log` 에 2행 기록 (module=tradingagents).

| 모델 | 호출 | 입력 토큰 | 출력 토큰 | 비용 |
| :--- | ---: | ---: | ---: | ---: |
| claude-haiku-4-5 (quick) | 11 | 117,991 | 40,445 | $0.320 |
| claude-sonnet-5 (deep) | 2 | 38,431 | 4,107 | $0.118 |
| 합계 | 13 | 156,422 | 44,552 | **$0.438** |

| 필드 | 글자 수 | 한글 비율 | 검토 표현 수 (`review_word_hits`) |
| :--- | ---: | ---: | ---: |
| market_report | 4,679 | 0.77 | 14 |
| news_report | 3,992 | 0.78 | 6 |
| bull | 7,076 | 0.84 | 25 |
| bear | 10,165 | 0.87 | 12 |

발견한 것
1. **결론 줄 필터 버그 (고침)**: 실제 출력은 `**Rating:** BUY / STRONG ACCUMULATION`, `**Rating:** SELL / AVOID` 형태라 `**Rating**:` 만 잡던 정규식이 놓쳤다. `\bRating\b[*\s]*:` (대소문자 무시)로 고치고 저장된 JSON 에도 다시 적용했다.
2. **토론은 그대로 못 쓴다**: 낙관 쪽 끝에 "단계별 매수 전략"(진입 비중 30·40·30%, 손절가, 6개월 목표 280~320달러 +70~95%), 비관 쪽 끝에 "즉각적 행동 권고사항"(전량 매도 권고, 목표 진입가 100~120달러)이 있다. 줄 단위 필터로는 지울 수 없고, 토론 본문 전체가 매매 권유 논조다 (CLAUDE.md 10번).
3. **한국어 품질**: 읽을 수는 있으나 오역·오타가 있다. "강세론" 대신 "강기론" 38회, "낙저점", "벌링턴 해서웨이" 등. 리포트 안 숫자(RSI 24.86, 이동평균 등)는 라이브러리가 계산한 값이라 우리 코드 값과 대조하지 않으면 쓸 수 없다.
4. **뉴스 사실 확인 필요**: news_report 가 "Jensen Huang CEO 사임"을 최고 위험 요인으로 든다. yfinance 뉴스 원문과 대조하지 않았고, 뉴스가 분석 날짜로 걸러지지 않는다는 점도 그대로다.
5. **시간**: 1회 15분. 매일 배치로는 가능하지만 사용자 요청 시 실시간 생성은 안 된다.

## 결론 (2026-11-16, A 결정)

**TradingAgents 는 쓰지 않는다.** 토론만 필요한데 토론만 떼어 돌릴 수 없어(분석가 → 토론 → 트레이더·리스크·최종 결정이 한 그래프) 버릴 단계까지 비용을 낸다.

대신 판단해보기 AI 분석 피드백에 쓸 토론을 직접 만든다.
- 낙관 에이전트 → 비관 에이전트(낙관 발언을 보고 반박) 2개. 카드마다 하루 1번 미리 만들어 DB 에 저장한다 (카드 내용에만 달려 있어 사용자 답과 무관).
- 정리 역할은 따로 두지 않는다. 이미 답안마다 1번 부르는 `generate/judge.py` 가 토론을 입력으로 받아 "더 생각할 점"을 쓴다.
- 재료는 카드의 key_facts·chain·counter (코드·DB 가 정한 사실). 데이터를 찾아오는 단계가 없어 입력이 수천 토큰이다.
- 추정 비용: 카드 1장 토론 약 $0.001 (haiku 2회), 답안당 judge 입력 증가 약 $0.002. 실측은 구현 후 llm_cost_log 로 확인.

## 설치본에서 확인한 사실

- `final_state` 필드 (설치본 `agents/state.py` 의 `AgentState`, 실행 때 `final_state.keys()` 로 다시 확인): `market_report`, `sentiment_report`, `news_report`, `fundamentals_report`, `investment_debate_state`(`bull_history`, `bear_history`, `history`, `current_response`, `count`), `investment_plan`, `trader_investment_plan`, `risk_debate_state`, `final_trade_decision`, `final_rating`, `past_context`, `memory_note`, `portfolio_context` 외
- 저장하는 것: `market_report`, `news_report`, `investment_debate_state.bull_history`, `bear_history`
- 버리는 것: `investment_plan`, `trader_investment_plan`, `risk_debate_state`, `final_trade_decision`, `final_rating`, `propagate()` 의 두 번째 반환값(Buy~Sell). 텍스트 안의 `**Rating**:`·`**Rating:**`·`FINAL TRANSACTION PROPOSAL` 줄도 지운다. "매수·매도·Buy·Sell" 등은 지우지 않고 필드별 개수(`review_word_hits`)로 남겨 사람이 본다.
- 언어: 설정 파일 주석은 "토론은 영어로 유지"라고 하지만, 0.7.1 에서는 낙관·비관 연구원 프롬프트에도 `get_language_instruction()` 이 붙어 토론도 한국어로 나올 것으로 본다. 한국어 비율이 50% 미만인 필드만 `claude-haiku-4-5` 로 번역한다 (사용자 결정: 토론은 한국어로 저장). 번역한 필드는 `translated_fields` 에 남는다.

## C 에게 넘길 출력 형식 (통과하면)

```json
{
  "ticker": "NVDA",
  "analysis_date": "2026-11-16",
  "source": "TradingAgents 0.7.1",
  "reports": { "market_report": "한국어 기술적 분석 리포트", "news_report": "한국어 뉴스·거시 리포트" },
  "debate": { "bull": "낙관 연구원 발언", "bear": "비관 연구원 발언" },
  "meta": {
    "models": { "quick": "claude-haiku-4-5", "deep": "claude-sonnet-5" },
    "analysts": ["market", "news"], "max_debate_rounds": 1, "output_language": "Korean",
    "translated_fields": [], "hangul_ratio": {}, "review_word_hits": {},
    "graph_seconds": 0, "total_seconds": 0,
    "usage": [{ "model": "...", "calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0 }],
    "cost_usd": 0
  }
}
```

- 탭 1 해설 재료로만. 숫자는 이 문장에서 뽑지 않는다 (숫자는 우리 코드가 계산).
- 뉴스는 분석 날짜로 걸러지지 않아 "그날 이전 자료만" 보장이 없다. 탭 2 근거에 쓰지 않는다.
- `review_word_hits` 가 0 이 아닌 필드는 금지 표현 검사(매수·매도 권유)를 거친 뒤에만 쓴다.
- generate/ 코드는 이 시험에서 바꾸지 않았다. 연결 방법은 C 가 정한다.
