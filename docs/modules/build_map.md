> **초안 (Claude 작성, 2026-11-23).** 담당자 사람1이 읽고 고쳐서 확정한다.

# worker/concepts/build_map.py

- **한 줄 설명**: 개념 지도를 한 번에 만든다. ① 재료 → ② 용어 뽑기 → ③ 같은 뜻 묶기 → ④ 선수 관계 다수결 → ⑤ 저장 (#198). 단계별 코드는 concept_map.py(①②), term_groups.py(③), prereq_votes.py(④)에 있고 여기서는 잇기만 한다.
- **입력**: DB의 카드 concept 단계 용어(①), 임베딩 모델(기본 KURE-v1, 기준 0.70). 실행은 `cd worker && python -m concepts.build_map`. 기본은 ①③만 돌아서 LLM 비용이 없다. `--extract`는 ②, `--prereq`는 ④를 켠다(Haiku 비용). `--max-pairs N`은 ④ 후보 쌍 상한, `--threshold`와 `--model`은 ③ 설정이다.
- **하는 일**: 용어를 임베딩해 묶고 노드를 만든다. ④를 켜면 노드 대표 이름을 다시 임베딩해서 후보 쌍(같은 카드 + 가까운 이웃)을 고르고 4번씩 묻는다. 노드 id는 파일 안에서만 쓰는 `c001`, `c002` …이다. DB id는 009 마이그레이션에서 새로 매긴다.
- **출력 (⑤)**: 사람2의 009 마이그레이션 전이라 DB 대신 파일로 남긴다 (Git에 안 올라감). `logs/concept_map/concept_map.json`에는 설정, 개수, 노드(`id, label, desc, aliases, card_ids`), 선수 관계(`pre_id, post_id, votes, total`), 검토 목록이 들어 있다. 계획 6장 테이블 초안과 같은 이름이라, 테이블이 생기면 이 파일을 그대로 넣는다. `logs/concept_map/groups_review.tsv`는 두 용어 이상 묶인 노드만 **묶음 안 최저 유사도가 낮은 것부터** 보여 준다. 의심스러운 묶음부터 사람이 훑어보고 마지막 칸에 O를 표시한다 (엑셀에서 한글이 안 깨지게 BOM을 붙인다). 화면에는 완료 기준 로그를 출력한다: 용어 N개 → 노드 N개, 선수 관계 N개, ④ 호출·갈림·관계 없음 수.
- **주의할 점**: 순환 검사는 아직 없다. ④ 결과에 순환이 있을 수 있고, 1-2 `prereq.dl`이 검사하고 끊는다. ② 입력은 아직 1차 자료 제목이다. 실제 제목이 "MICROSOFT CORP 8-K Item 2.02" 같은 모양이라 용어가 거의 안 나올 수 있어서, 카드뉴스 글로 바꿀지 정해야 한다.
- **테스트**: `cd worker && python -m pytest tests/test_build_map.py -q` (DB·모델·API 없이 가짜 임베딩과 가짜 답: 묶기만, 검토 목록 순서, ④까지 연결·개수, 빈 입력, 저장 파일 모양).
