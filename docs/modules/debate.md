> 초안 (Claude 작성). 담당자 A 가 읽고 고쳐서 확정한다.

# worker/generate/debate.py

- **한 줄 설명**: 판단해보기 AI 분석 피드백의 재료로, 카드마다 낙관·비관 토론을 하루 1번 미리 만들어 `card_debates`에 저장한다. TradingAgents 대신 쓴다(#102 결론, docs/tradingagents-trial.md).
- **입력**: `card_id` 목록. DB에서 카드 제목·카드뉴스(slides)·`key_facts`와 판단해보기 단계의 질문·상황·선택지·`chain`·`counter`(개념 이름으로 풀어서)를 읽는다.
- **하는 일**: ① 낙관 에이전트(Haiku)가 사건이 유리하게 작용하는 해석을 chain 순서로 쓴다 → ② 비관 에이전트(Haiku)가 낙관 발언을 받아 counter·위험으로 반박한다 → ③ 발언마다 코드 검사(입력에 없는 숫자, `find_banned` 금지 표현, 판단해보기 선택지 이름, 300자)를 하고, 걸리면 까닭을 주고 1번 고쳐 쓰게 한다 → ④ 둘 다 통과하면 `published`, 아니면 `rejected`로 덮어쓴다(P21). 낙관이 실패하면 비관은 부르지 않는다.
- **출력**: `card_debates` 한 줄(`bull`, `bear`, `status`, `model_info` = 모델·호출 수·실패 까닭). 비용은 `llm_cost_log`(module=`debate`, card_id 포함). CLI 는 결과 JSON 을 출력한다.
- **쓰는 곳**: `run_daily.py` 의 "토론" 단계(출제 다음). Spring `findStep`이 published 토론을 읽어 채점 서버에 `debate`로 넘기고, `judge.py`가 "더 생각할 점"에서 답안이 다루지 않은 쪽 시각을 짚는 데 쓴다. 점수 기준은 바꾸지 않는다. 화면에 토론 원문을 따로 보여 주지 않는다.
- **주의할 점**: 선택지 이름 금지는 토론이 어느 선택을 권하지 못하게 하는 장치다(띄어쓰기 무시). 선택지가 짧은 일반어면 정상 문장도 걸릴 수 있어 rejected 비율을 본다. "100만 원 배분" 처럼 낙관·비관으로 나뉘지 않는 문제도 지금은 같은 틀로 만든다. 추정 비용 카드 1장 약 $0.001(실측 전).
- **실행**: `python -m generate.debate --card-id 12`, `--date 2026-11-16`(토론 없는 카드만), `--force`(다시 만들기), `--dry-run`(저장 안 함).
- **테스트 순서**: `python -m pytest tests/test_debate.py -q`(숫자·금지 표현·선택지·길이 검사, 낙관→비관 순서와 비관 입력의 `<bull>`, 고쳐 쓰기, 실패 시 rejected, 저장 SQL) → `tests/test_judge.py`의 토론 테스트(프롬프트 데이터에 들어가고 점수는 그대로) → 실제 카드 1장으로 `--dry-run` → `card_debates`와 `llm_cost_log` 확인.
