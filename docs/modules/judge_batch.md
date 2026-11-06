> **초안 (Claude 작성, 2026-11-05).** 담당자 A가 읽고 고쳐서 확정한다.

# worker/scripts/judge_batch.py

- **한 줄 설명**: 판단 근거 답안 여러 개를 한 번에 채점해 CSV로 쓴다. 8주차에 답안 40개를 채점해 C의 κ 계산에 넘기는 용도다.
- **입력**: 답안 CSV(`id`, `answer` + `step_id` 또는 `key_facts`·`chain`·`counter` JSON 열, 선택 `card_id`). `--rule-only`면 Claude를 부르지 않는다.
- **하는 일**: 줄마다 채점 재료를 준비한다(`step_id`가 있으면 DB의 cards.key_facts·steps.answer의 개념 id를 concepts 이름·별칭으로 바꿈). 그다음 `judge.grade`(또는 규칙 채점)를 부른다. 한 줄이 실패해도 멈추지 않는다.
- **출력**: UTF-8 BOM CSV(`id, evidence, reasoning, rebuttal, total, score, grader, reasoning_reason, rebuttal_reason, error`). 엑셀에서 바로 열린다.
- **주의할 점**: Claude 채점은 답안마다 1회 호출이라 비용이 든다(llm_cost_log에 module='judge'로 기록). κ는 기준별로 비교하므로 evidence·reasoning·rebuttal 열을 쓴다. `grader=rule` 줄은 Claude가 실패한 답안이라 κ 비교에서 빼거나 다시 돌린다.
- **실행**: `cd worker && python -m scripts.judge_batch answers.csv scores.csv [--rule-only]`
- **테스트**: `python -m pytest tests/test_judge_batch.py -q` (JSON 열 방식 규칙 채점 89·22점, step_id 로더 사용, 잘못된 줄은 error에 남기고 계속).
