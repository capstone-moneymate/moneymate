> **초안 (Claude 작성, 2026-11-05).** 담당자 A가 읽고 고쳐서 확정한다.

# worker/judge_api.py

- **한 줄 설명**: 판단해보기 주관식 근거를 채점하는 FastAPI 서버. Spring Boot의 `/api/judgement`가 HTTP로 부른다 (#54).
- **입력**: `POST /judge` JSON. `answer`(1~2000자, 필수), `key_facts`(`[{"text","keywords"}]`), `chain`·`counter`(`[{"name","aliases"}]`, 개념 id가 아니라 **이름·별칭으로 풀어서**), `card_id`·`step_id`(선택). `GET /health`는 입력 없음.
- **하는 일**: `generate/judge.py`가 있으면 `judge.grade()`를, 없으면 `rule_judge.grade()`를 부른다. `judge.grade()`가 예외를 올리면 규칙 채점으로 한 번 더 받아 500을 내지 않는다. DB는 읽지 않는다.
- **출력**: `rubric`(증거·추론·반박), `total`(0~9), `score`(0~100), `matched_facts`, `matched_concepts`, `grader`("claude"/"rule"), `reasons`(Claude 채점 이유 `{reasoning, rebuttal}`, 규칙 채점이면 빈 객체). `/health`는 `{"status":"ok","grader":"judge"|"rule"}`.
- **주의할 점**: 개념 id → 이름·별칭 변환, 하루 호출 제한, 같은 답안 해시 재사용, 실패 시 고정 문구는 Spring `/api/judgement`(#55 2차) 몫이다. Claude 채점은 `generate/judge.py`(#55)가 하고, 비용 기록·월 한도는 C의 `llm_client.py`로 한다(module='judge'). judge.py 파일이 없을 때만 규칙 채점으로 가고, judge.py 안의 import 오류는 서버 시작 때 그대로 드러낸다. AI 분석 피드백(잘한 점·더 생각할 점·인과 뼈대)은 #56이다.
- **실행**: `cd worker && uvicorn judge_api:app --port 8000` 또는 레포 루트에서 `docker compose up -d judge` (포트는 `.env`의 `JUDGE_API_PORT`).
- **테스트**: `python -m pytest tests/test_judge_api.py -q` (health, 손계산 만점 9/9 → 100, 개념만 2/9 → 22, counter 생략, 잘못된 요청 422, judge.py 있으면 사용, judge.py 예외 시 규칙 채점 전환). judge.py 연결은 `tests/test_judge.py`에서 확인한다.
