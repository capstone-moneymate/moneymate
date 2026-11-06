> **초안 (Claude 작성, 2026-11-05).** 담당자 A가 읽고 고쳐서 확정한다.

# worker/generate/judge.py

- **한 줄 설명**: 판단해보기 주관식 근거를 루브릭 9점(증거 0~2 코드 · 추론 0~4 / 반박 0~3 Claude)으로 채점하고, 같은 호출에서 AI 분석 피드백(잘한 점·더 생각할 점·인과 뼈대)을 만든다. Claude가 실패하면 규칙 채점과 고정 문구로 넘어간다 (#55·#56).
- **입력**: `grade(text, key_facts, chain, counter=None, card_id=None)`. 형식은 rule_judge와 같다(`key_facts` = `[{"text","keywords"}]`, `chain`·`counter` = `[{"name","aliases"}]`). 프롬프트는 `generate/prompts/judge.md`(기준별 점수 설명, 점수별 예시 답안, 피드백 쓰는 법).
- **하는 일**:
  1. rule_judge로 증거 점수, 찾은 사실·개념, 대체 결과를 먼저 계산한다.
  2. Sonnet을 **1회** 부른다(llm_client.create, module='judge', JSON 스키마 출력, 루브릭 프롬프트 캐시). 1의 결과를 `code_result`로 넘겨 피드백이 점수와 어긋나지 않게 한다.
  3. 추론·반박을 0~배점으로 자르고, 총점은 합계로 다시 계산한다(모델의 총점·증거는 무시).
  4. **인과 뼈대 경로는 코드가 만든다**(chain 순서 + 답안에 있는 개념이면 `used`). Claude는 설명 한 문장만 쓴다.
  5. 이유·피드백 문장에 금지 표현(B의 `validators.find_banned`, 목록은 `validate/banned_terms.txt`)이 있으면 **그 항목만** 고정 문구로 바꾼다.
- **출력**: `JudgeResult(rubric, total, score, matched_facts, matched_concepts, grader, reasons, feedback, error)`. `feedback` = `{"good", "think_more", "chain": [{"name","used"}], "chain_comment"}`.
- **주의할 점**: API·연결 오류, 월 한도 초과, 응답 잘림, JSON·필드 오류, 정수나 문자열이 아닌 값은 모두 규칙 채점으로 받는다. 이때 피드백은 "근거 있는 선택이었어요." / "이런 경우도 생길 수 있어요." + 코드 인과 뼈대 + 코드가 만든 설명이다. 이 고정 피드백(`fallback_feedback`·`chain_path`)은 `rule_judge.py`에 있고, judge.py는 같은 이름으로 다시 쓴다(judge_api의 대체 경로도 같은 함수를 쓴다). 피드백은 사용자의 선택을 평가하지 않고, 문장마다 80자 안팎으로 쓰게 프롬프트로 안내한다(코드가 자르지는 않는다). 답안은 `<data>` JSON 안에 넣어 넘긴다. `EFFORT="low"`는 응답 속도를 위한 임시값으로, κ(8주차)를 보고 정한다. **실제 Claude 호출은 아직 확인 전이다 (A의 API 키 필요).**
- **테스트**: `python -m pytest tests/test_judge.py -q` (Claude는 가짜. 증거는 코드 값, 모델 총점 무시, 범위 자르기, 금지 표현 항목별 대체, 실패 11가지 → 규칙 채점 + 고정 피드백, 인과 뼈대 used, code_result 전달, judge_api 연결).
