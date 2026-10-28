> **초안 (Claude 작성, 2026-10-28).** 담당자 C가 읽고 고쳐서 확정한다.

# worker/generate/llm_client.py

- **한 줄 설명**: Claude 호출 공통 모듈. 월 한도를 확인하고, 호출하고, 비용을 `llm_cost_log` 에 남긴다. classify·compose·reasons 는 Claude를 이 모듈로만 부른다.
- **입력**: `create(module, card_id=None, note=None, **params)`. params 는 `messages.create` 인자 그대로 (model, max_tokens, messages, tools ...). `.env` 의 `ANTHROPIC_API_KEY`, `LLM_MONTHLY_LIMIT_USD`(기본 10).
- **하는 일**: ① 이번 달(KST 1일 0시부터) 누적 비용이 한도 이상이면 `BudgetExceeded` 로 호출을 막는다. ② `messages.create` 호출 (429·5xx·연결 오류는 SDK가 2회 재시도, 그래도 실패하면 예외를 그대로 올림). ③ `resp.usage` 로 비용을 계산해 1줄 기록.
- **출력**: SDK 응답(`Message`) 그대로. `text_of(resp)` 는 text 블록만 이어 붙인다. 기록: `llm_cost_log` (input_tokens = 일반+캐시 쓰기+캐시 읽기 합, note 에 request_id·stop_reason·캐시 토큰). DB에 못 쓰면 `logs/llm_cost_log.jsonl`, 한도 계산도 그 파일로 대신한다.
- **주의할 점**: 단가는 코드의 `PRICES` (2026-10, USD/1M 토큰: Haiku 5.5 $0.10/$0.50, 100K 넘는 입력은 $0.50/$2.50; Sonnet 5.5 $2/$10). 캐시 쓰기 1.25배·읽기 0.1배. 가격이 바뀌면 고친다. 한도는 호출 **전**에 확인하므로 마지막 1회가 한도를 조금 넘길 수 있다. 문제 1개당 비용은 `card_id` 로 묶어 집계한다 (카드 저장 전 호출은 card_id 없이 기록되므로 compose 에서 저장 후 채우는 방법을 정해야 함).
- **테스트**: `cd worker && python -m pytest -q tests/test_llm_client.py` — 비용 손계산 4개(기본·캐시·긴 입력), KST 월 경계, 한도 차단/통과, 가짜 클라이언트로 기록·차단 확인. 실제 API·DB는 부르지 않는다.
