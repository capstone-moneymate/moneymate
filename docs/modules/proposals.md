> **초안 (Claude 작성, 2026-11-07).** 담당자 B가 읽고 고쳐서 확정한다.

# worker/concepts/proposals.py

- **한 줄 설명**: 1차 자료에 맞는 개념이 사전에 없을 때 LLM이 새 개념과 연결을 제안하고, 코드가 걸러 팀이 검토할 후보로 남긴다. 사전은 고치지 않는다.
- **입력**: 자료 한 건(`title`, `category`, `ticker` 등, `classify.build_user`와 같은 모양)과 `db/seeds`의 개념 사전. 실행은 `cd worker && python -m concepts.proposals "제목" 분류 [종목]`, 후보를 저장하려면 `--save`. 호출마다 Haiku를 2번 부른다(`llm_client`로 월 한도·비용 기록, module=`proposals`).
- **하는 일**: ① 같은 자료로 독립 호출 2회. 기존 개념 id를 JSON 스키마 enum으로 묶어 연결이 사전 밖을 가리킬 수 없고, 한쪽은 항상 새 개념이다. ② 개념 id와 연결·방향이 같아야 통과(이름·이유 문장은 달라도 된다). ③ 코드 검사: id 형식, 기존 개념의 id·이름·별칭과 겹치지 않음(띄어쓰기·대소문자 무시, 겹치면 별칭 후보), 연결 1개 이상, 한 쌍에 방향 하나, 합친 사전에 순환 없음.
- **출력**: `Outcome(status, proposal, errors)`. status는 `none`(2회 모두 제안 없음), `mismatch`(2회가 다름), `rejected`(코드 검사 실패), `candidate`(후보). `--save`를 붙이면 후보만 `logs/concept_proposals.jsonl`에 한 줄 추가한다(`verified: false`, Git에 올라가지 않음). 같은 개념이 여러 자료에서 나오면 줄이 쌓여 빈도를 볼 수 있다.
- **주의할 점**: 후보는 정답으로 쓸 수 없다. `reasons`는 LLM의 설명이지 근거가 아니어서, 방향은 사람이 1차 자료로 확인한 뒤(`concept_dictionary.md` 기준 4) CSV에 넣는다. 2회 일치는 답이 안정적이라는 뜻이지 맞다는 뜻이 아니다. 두 호출이 같은 프롬프트라 같은 착각을 반복할 수 있다. 개념 id 표현이 달라도(`fx_rate` / `won_dollar`) `mismatch`로 걸러지는 보수적인 방식이다. DB가 비어 있어도 같은 사전을 보도록 CSV를 읽는다. 전용 테이블 없이 파일로 시작했고, 출제 파이프라인 연결은 C와 6주차에 정한다.
- **테스트**: `cd worker && python -m pytest tests/test_proposals.py -q` (가짜 응답: 2회 일치, 제안 없음, 불일치 5가지, 기존 개념 중복·id 형식·연결 없음·방향 충돌, 순환, 잘린 응답, 스키마, 후보 저장). **실제 API로는 아직 확인하지 못했다**(2026-11-07 B의 `.env`에 `ANTHROPIC_API_KEY` 없음). 스키마가 실제로 받아들여지는지, 비용과 제안 품질은 키를 받은 뒤 확인한다.
