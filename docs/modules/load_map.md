> **초안 (Claude 작성, 2026-11-24).** 담당자 사람1이 읽고 고쳐서 확정한다.

# worker/concepts/load_map.py

- **한 줄 설명**: 개념 지도(`logs/concept_map/concept_map.json`, build_map이 만듦)를 사람2의 009 테이블 `concept_nodes`, `concept_node_cards`, `concept_prereq`에 넣는다 (#224, 계획 1-1 ⑤).
- **입력**: concept_map.json (노드 `id, label, desc, aliases, card_ids`, 선수 관계 `pre_id, post_id, votes, total`), DB의 `cards`, 그리고 탭 1 단어 목록 `concepts`의 **이름·별칭만** (인과 화살표 `causal_edges`는 읽지 않는다). 실행은 `cd worker && python -m concepts.load_map` (`--path`로 다른 파일). 지도를 다시 만들면(`build_map`) 이것도 다시 돌린다.
- **하는 일**: 노드는 이름(label)으로 맞춰 넣거나 고친다(설명은 빈칸이면 원래 것을 두고, 별칭은 더하기만). 지도 노드의 카드 연결은 지도대로 바꾸고, DB에 없는 카드는 건너뛴다. `concept_prereq`는 지도만 쓰는 표라 통째로 지도대로 바꾼다. 사람이 keep / add 한 연결은 지도에서 5표(순환을 끊을 때만 쓰는 값)라 표 규칙 `total >= votes`에 맞게 **4 / 4**로 넣는다. **탭 1 단어 짝짓기**(`causal_id`, 사람2가 009에 만든 칸): 노드 이름·별칭이 탭 1 개념 이름·별칭과 글자가 같을 때만 짝짓는다(`term_key`: 띄어쓰기·대소문자·괄호 무시). 인과 관계를 만들거나 쓰는 게 아니라 **같은 단어라는 이름표**다. 짝지으면 본 문제에서 맞힌 개념과 튜터 퀴즈의 개념이 알 확률 하나를 함께 쓴다. `concepts` 표는 고치지 않는다.
- **출력**: 세 테이블. 개수 요약(노드, 카드 연결, DB에 없는 카드, 선수 관계, 탭 1 단어 짝짓기, 애매해서 안 짝지음, 다른 노드가 가져서 안 짝지음, 지도에 없는 DB 노드)을 출력한다. 커밋은 `main`의 `with get_conn()`이 끝까지 성공했을 때만 한다.
- **실제 결과 (2026-11-24)**: 노드 38개, 카드 연결 167개, 선수 관계 42개, 탭 1 단어 짝짓기 11개 (매출액=revenue, 당기순이익=corp_earnings, 주당순이익(EPS)=eps, 자사주 취득=buyback 등. 담당자가 11개 모두 확인, 2026-11-24). 넣은 뒤 `learner.state.get_mastery`가 개념 38개를 돌려준다.
- **주의할 점**: 지도에서 빠진 노드는 **지우지 않는다**. 지우면 `user_concept_state`가 함께 지워져 학습 기록이 사라진다(ON DELETE CASCADE). 개수만 알려 준다. 사람2의 `update_causal`은 본 문제 답에서 탭 1 개념 노드를 스스로 만든다(이름 = `concepts.name`). 그래서 이미 다른 노드가 가진 개념은 빼앗지 않고(`causal_id` UNIQUE), 이미 짝지어진 노드는 그대로 둔다. 한 노드가 여러 개념에, 또는 한 개념이 여러 노드에 걸리면 애매해서 짝짓지 않는다. 짝이 없으면 튜터 퀴즈(개념 지도)와 본 문제(탭 1)의 알 확률이 따로 논다. 이름이 조금 다르면(매출액 / 매출) 사람2 코드가 같은 개념의 노드를 하나 더 만든다.
- **테스트**: `cd worker && python -m pytest tests/test_load_map.py -q` (탭 1 단어 짝짓기는 DB 없이: 이름·별칭·띄어쓰기·괄호, 애매한 경우 두 가지 / 실제 PostgreSQL, 끝에 rollback: 노드·카드·선수 관계와 사람 표 4/4, 두 번 넣어도 지도대로(연결 빠짐, 설명 유지, 별칭 더하기), 지도에서 빠진 노드의 학습 기록 유지, 탭 1 단어 짝짓기와 빼앗지 않기, 짝지은 뒤 `update_causal`이 지도 노드 알 확률을 고침). DB가 없거나 009가 없으면 DB 테스트는 건너뛴다.
