> **초안 (Claude 작성, 2026-11-07).** 담당자 B가 읽고 고쳐서 확정한다.

# worker/concepts/loader.py

- **한 줄 설명**: `db/seeds`의 개념 사전 CSV를 `concepts`, `causal_edges` 테이블에 넣어 DB를 CSV와 맞춘다.
- **입력**: `db/seeds/concepts.csv`, `causal_edges.csv`. 실행은 `cd worker && python -m concepts.loader`(결과만 출력, 되돌림), `--save`(DB에 반영).
- **하는 일**: 먼저 사전을 검사한다(개념 id·연결 중복, 사전에 없는 개념, `force_dir` 오타, 순환. `graph.py`의 `build_graph`, `find_cycle`을 그대로 쓴다). 잘못되면 DB에 넣기 전에 `ValueError`로 멈춘다. 그다음 개념과 연결을 넣고, 이미 있으면 이름·별칭·방향·note를 CSV 값으로 덮어쓴다. `aliases`는 `;`로 나눠 `TEXT[]`로 넣는다. CSV에서 지운 연결은 DB에서도 지운다.
- **출력**: 개념·연결 개수, 지운 연결, CSV에 없는데 DB에 남은 개념을 출력한다.
- **주의할 점**: CSV가 원본이라 DB에서 직접 고친 값은 다음 적재 때 덮어쓴다. 개념은 CSV에서 지워도 DB에서 지우지 않고 경고만 한다. `cards.start_concept`, `user_concepts`가 참조할 수 있어서, 참조를 확인한 뒤 사람이 지운다. `graph.py`와 `validators.py`는 지금도 CSV를 직접 읽고, `classify.py`는 DB를 먼저 읽는다. 그래서 CSV를 고치고 `--save`를 안 돌리면 둘이 어긋날 수 있다. 자동 실행은 없으니 DB를 새로 만들거나 CSV를 고치면 직접 돌린다.
- **테스트**: `cd worker && python -m pytest tests/test_loader.py -q` (별칭 나누기, CSV 읽기, 잘못된 사전 5가지 거부, 실제 사전 17개·14개, 가짜 연결로 지운 연결 삭제·개념 유지). 2026-11-07 로컬 DB에서 확인: 미리보기는 DB를 바꾸지 않음, `--save` 후 17개·14개, 두 번 돌려도 같음, 트랜잭션 안에서 옛 연결과 개념을 넣으면 연결은 지우고 개념은 경고(되돌림), `classify.load_concepts`가 17개, `load_edges`가 14개를 읽음.
