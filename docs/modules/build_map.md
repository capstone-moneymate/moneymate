> **초안 (Claude 작성, 2026-11-23, 2026-11-24 #203 반영).** 담당자 사람1이 읽고 고쳐서 확정한다.

# worker/concepts/build_map.py

- **한 줄 설명**: 개념 지도를 한 번에 만든다. ① 재료 → ② 용어 뽑기 → ③ 같은 뜻 묶기 → ④ 선수 관계 다수결 → 순환 검사 → ⑤ 저장 (#198, #203). 단계별 코드는 concept_map.py(①②), term_groups.py(③), prereq_votes.py(④), prereq_check.py(순환)에 있고 여기서는 잇기만 한다.
- **입력**: DB의 카드 concept 단계 용어와 슬라이드 글(①), 사람 검토 파일 두 개 `worker/concepts/term_review.csv`(②)와 `prereq_review.csv`(④), 임베딩 모델(기본 KURE-v1, 기준 0.90). 실행은 `cd worker && python -m concepts.build_map`. 기본은 LLM 없이 ①③과 두 검토 파일만 써서 비용이 0이고, 같은 DB·같은 검토 파일이면 같은 지도가 나온다. `--extract`는 ②, `--prereq`는 ④를 다시 돌린다(Haiku 비용). 새로 나온 결과는 검토 파일에 빈칸 줄로 더해지니, 사람이 decision을 채운다. `--max-pairs N`은 ④ 후보 쌍 상한, `--threshold`와 `--model`은 ③ 설정이다.
- **하는 일**: 순서는 ① 재료 모으기 → 임베딩 모델 불러오기 → `term_review.csv` 반영(keep / same) → (`--extract`면 ② 뽑기, 같은 뜻은 임베딩 0.80으로 한 번 더 확인, 후보를 검토 파일에 저장) → ③ 묶기와 헷갈리는 이웃 → (`--prereq`면 ④ 다수결, 새 연결을 `prereq_review.csv`에 저장) → `prereq_review.csv`에서 drop만 빼고 선수 관계를 만듦 → 순환 검사(`break_cycles`: 순환 위 연결 중 표가 가장 적은 것부터 뺌) → 저장. 노드 id는 파일 안에서만 쓰는 `c001`, `c002` …이다. DB id는 009 마이그레이션에서 새로 매긴다.
- **출력 (⑤)**: 사람2의 009 테이블에 넣기 전까지 파일로 남긴다 (`logs/`라 Git에 안 올라감). `concept_map.json`에는 설정, 개수, 노드(`id, label, desc, aliases, card_ids`), 선수 관계(`pre_id, post_id, votes, total`), 순환으로 뺀 연결(`prereqs_removed_for_cycles`), 검토 파일에 있지만 지도에 없는 이름(`prereq_review_missing`, 용어가 바뀌었을 때 확인), 헷갈리는 이웃(`confusable`: 튜터의 "헷갈리는 쌍" 퀴즈 재료, `tutor/agent.py`가 읽음), 묶음 검토 목록이 들어 있다. `groups_review.tsv`는 두 용어 이상 묶인 노드를 묶음 안 최저 유사도가 낮은 것부터, `prereq_review.tsv`는 선수 관계와 순환으로 뺀 연결을 보여 준다 (엑셀에서 한글이 안 깨지게 BOM). 화면에는 검토 반영 개수, 용어 N개 → 노드 N개, 선수 관계 N개를 출력한다.
- **실제 카드 결과 (2026-11-24)**: 카드 25장, 용어 38개(② 검토로 15개) → 노드 38개, 선수 관계 42개, 순환으로 뺀 연결 1개(자사주 취득 → 자기주식), 헷갈리는 이웃이 있는 노드 17개.
- **주의할 점**: 검토 파일 두 개가 지도의 "정답지"라 Git에 올리고, LLM 결과 파일(`logs/`)은 올리지 않는다. 용어 이름이 바뀌면 `prereq_review.csv`의 줄이 지도에서 사라질 수 있으니 `prereq_review_missing`을 본다. 순환으로 뺀 연결은 검토 파일에 빈칸으로 남아 있고 만들 때마다 다시 검사한다.
- **테스트**: `cd worker && python -m pytest tests/test_build_map.py -q` (DB·모델·API 없이 가짜 임베딩과 가짜 답: 묶기만, 기준값 0.90, 헷갈리는 이웃, 검토 목록 순서, ④까지 연결·개수, 순환 끊기와 검토 표, 선수 관계 검토 파일 반영, 빈 입력, 저장 파일 모양, 튜터가 confusable을 읽음).
