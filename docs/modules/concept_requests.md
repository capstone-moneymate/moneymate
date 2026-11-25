> **초안 (Claude 작성, 2026-11-26).** 담당자 사람1이 읽고 고쳐서 확정한다.

# worker/concepts/concept_requests.py

- **한 줄 설명**: 매일 만든 카드의 "개념" 단계 용어 중 개념 지도에 없는 것을 찾아, LLM 이 쓴 요청서와 함께 `logs/concept_requests.jsonl` 에 쌓는다 (#266). 탭 1 인과 사전 제안(`concepts/proposals.py`)과 같은 규칙으로, LLM 은 후보만 내고 지도는 사람이 검토 파일에서 정한 뒤에만 바뀐다.
- **입력**: DB 의 카드 개념 단계 용어(`steps.content.terms`)와 지도 노드 이름·별칭(`concept_nodes`), 검토 파일 `term_review.csv`(이미 본 용어는 건너뜀), 지금까지의 요청 파일. 실행은 `run_daily` 의 마지막 단계 "개념 지도 새 용어 요청"(오늘 만든 카드), 또는 `cd worker && python -m concepts.concept_requests --cards 32 33` / `--since 2026-11-21`. `--to-review` 는 쌓인 요청을 검토 파일로 옮긴다(LLM 없음).
- **하는 일**: ① 새 용어 찾기(코드): 용어를 지도 이름·별칭과 `term_key`(띄어쓰기·대소문자·괄호 무시)로 맞춘다. 튜터의 `card_targets` 와 같은 규칙이라 "튜터가 못 가르치는 용어"와 같다. ② 요청서(Haiku, 같은 질문 2번): 지도의 같은 말(`same_as`), 뜻 한 문장, 먼저 알아야 할 지도 개념 0~2개. 지도 이름은 enum 이라 지어낼 수 없고, 선수 개념은 목록 길이 제한이 안 돼 칸 2개(`pre_1`, `pre_2`)로 받는다. 두 답의 같은 말·선수 개념(순서 무시)이 같으면 제안을 남기고, 다르면 제안 없이 용어만 남긴다(`agreed=false`). ③ 한 줄씩 더한다. 지도·DB 는 안 고친다.
- **검토 파일로 옮기기 (`--to-review`)**: 같은 말 제안은 `term_review.csv` 에 same_as 를 채운 **빈칸** 줄로 넣는다(사람이 decision 에 `same` 을 적어야 build_map 이 합친다). 새 개념은 메모만 남긴다(카드 개념 단계 용어라 build_map 이 스스로 노드로 넣는다). 선수 개념 제안은 `prereq_review.csv` 에 표 `2/2` 빈칸 줄로 넣는다(다른 LLM 연결과 같이 사람이 drop 하지 않으면 지도에 들어간다). 같은 줄이 있으면 더하지 않는다.
- **출력**: `logs/concept_requests.jsonl` (한 줄 = `requested_at, card_id, term, card_desc, agreed, suggestion{same_as, desc, prereqs}`). 배포에서는 scheduler 컨테이너의 `./logs` 가 서버 디스크에 남는다(docker-compose.prod.yml).
- **사람이 하는 순서**: 배포 서버의 요청 파일과 최신 DB 덤프를 받아 → `--to-review` → 검토 파일 decision 채우기 → `python -m concepts.build_map` → `python -m concepts.load_map` (로컬 확인 뒤 concept_map.json 을 배포 쪽에 전달).
- **주의할 점**: 새 용어가 있는 카드는 사람이 넣기 전까지 그 용어만 튜터가 못 가르치고(나머지 목표 개념은 가르침), 목표가 하나도 없으면 기존 개념 설명 화면으로 간다. 비용은 새 용어 하나에 Haiku 2번(1센트 미만). 2026-11-26 시험: 가짜 용어 "가동률" → 새 개념·선수 "생산능력", "설비 투자" → 같은 말 "신규 시설투자" (두 번 모두 일치). 카드 1~40 은 #262 로 지도에 다 들어가 새 용어 0개.
- **테스트**: `cd worker && python -m pytest tests/test_concept_requests.py -q` (지도 이름 enum, 두 답 일치·순서 무시·자기 자신 빼기·불일치면 제안 없음, 검토 파일 빈칸 줄과 두 번 불러도 같음 / 실제 PostgreSQL, 끝에 rollback: 띄어쓰기·괄호 무시로 있는 용어 빼기, 같은 새 용어 하나만, 이미 요청한 용어 다시 안 묻기).
