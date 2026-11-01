> **초안 (Claude 작성, 2026-10-12).** 담당자 C가 읽고 고쳐서 확정한다.

# worker/scripts/check_claude_call.py

- **한 줄 설명**: Claude를 1회 호출하고 토큰 수로 비용을 계산해 `llm_cost_log` 에 남기는 1회성 확인 스크립트.
- **입력**: `.env` 의 `ANTHROPIC_API_KEY` (Console 월 사용 한도를 먼저 설정), DB 연결(`config.DATABASE_URL`).
- **하는 일**: `claude-haiku-5-5` 에 짧은 질문 1개를 보내고, `resp.usage` 의 입력·출력 토큰에 모델 단가(USD/1M 토큰)를 곱해 비용을 계산한다.
- **출력**: 화면에 응답·토큰·비용 출력, `llm_cost_log` 에 1줄 INSERT (`module='week1_check'`, `note` 에 request_id). DB에 못 쓰면 `logs/llm_cost_log.jsonl` 에 대신 1줄.
- **주의할 점**: 단가는 코드에 적은 값(2026-10, 입력 100K 토큰 이하 구간)이라 가격이 바뀌면 고쳐야 한다. 생각(thinking) 토큰도 `output_tokens` 에 포함된다. 3주차 `generate/llm_client.py` 가 이 계산·기록 부분을 이어받는다.
- **테스트**: 1회성 스크립트라 pytest 없음. `docker compose up -d` 후 `cd worker && python scripts/check_claude_call.py` 실행 → `docker compose exec db psql -U moneymate -d moneymate -c "SELECT * FROM llm_cost_log"` 로 1줄 들어갔는지 확인.
