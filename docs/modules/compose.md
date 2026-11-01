> **초안 (Claude 작성, 2026-11-01).** 담당자 C가 읽고 고쳐서 확정한다.

# worker/generate/compose.py (+ prompts/compose.md)

- **한 줄 설명**: 출제 에이전트. Claude Sonnet이 1차 자료 1건과 유형·시작 개념을 받아 tools.py 도구로 숫자·경로를 얻고 카드뉴스·단계를 만든다. 코드가 검증하고 통과하면 `pending`으로 저장한다 (기술확정안 6·7·8단계).
- **입력**: `raw_sources` 한 행, classify 결과(`card_type`, `start_concept`), 카드 날짜. 개념 사전은 시스템 프롬프트 끝에 붙인다. 유형 3이면 그 종목을 담은 ETF의 최신 수량 변화(`holdings_etf`)를 함께 준다.
- **하는 일**: ① tool use 루프를 직접 돌린다 (`messages.create` + 도구 7개 + `submit_card`, effort medium, 대화 캐시). API 호출은 카드 1건에 `MAX_CALLS`(15)번까지. ② 에이전트가 `submit_card`로 카드를 내면 코드가 검사한다: 카드 모양(스키마), 유형별 단계 순서, 개념 id, 인과 순서(B의 validators), 차트 숫자(다시 계산), 보기·정답 번호, 금지 표현, key_facts. ③ 실패하면 이유를 `submit_card`의 오류 결과로 돌려줘 고치게 한다 (최대 3번). ④ 통과하면 `cards`(pending)·`card_sources`(is_main)·`steps`에 저장하고, 이 카드를 만든 호출의 `llm_cost_log.card_id`를 채운다.
- **출력**: `ComposeResult(card_id, card, errors, calls, repairs, cost_usd, request_ids)`. 끝내 통과하지 못하면 `card_id=None`, `errors`에 마지막 이유.
- **저장 모양**: `steps.content`는 화면에 내려보내는 부분(snake_case, `concept_ids` 포함), `steps.answer`는 서버만 보는 정답. quiz·chart `{correct, explanation}`(chart는 `check`도), causal_order `{correct: 경로, explanation, change, direction, evidence_quote}`, judgement `{chain, counter}`(A의 채점용). 인과 순서 보기는 자료 키로 고정 시드를 써서 섞고, 정답 순서와 같아지지 않게 한다.
- **정한 것 (팀 확인 필요)**: (1) 카드를 구조화 출력으로 받으면 `400 compiled grammar is too large`라서 `submit_card` 도구(이것만 strict 아님)로 받고 모양은 코드가 확인한다. (2) 금지 표현은 B의 검증기가 생기기 전까지 compose 안의 정규식으로 본다. (3) 검토 에이전트(독립 풀이)는 담당이 정해지면 `review` 인자로 붙인다. (4) 서버·화면은 camelCase라 서버가 `concept_ids` → `conceptIds`처럼 바꿔 내려야 한다.
- **비용 (실측 1건)**: 유형 3(SK하이닉스 HBM 공급계약), Sonnet 2회, 수정 0회, $0.031. 두 번째 호출은 6,086토큰 캐시 읽기. 유형 1·2는 가격 DB가 있어야 차트 검증이 돼서 DB를 띄운 뒤 측정한다.
- **테스트**: `cd worker && python -m pytest tests/test_compose.py -q` (정상 카드 통과, 13가지 불량 카드, 유형 3 순서, 모양 오류 4가지, steps 행·정답 분리·섞기, 가짜 Claude로 도구 → 제출, 수정 1회 후 통과, 수정 상한, 호출 상한, 글로만 답하면 제출 요청, 같은 턴 도구 + 제출, review 훅).
