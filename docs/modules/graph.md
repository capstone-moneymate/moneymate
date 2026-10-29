> **초안 (Claude 작성, 2026-10-29).** 담당자 B가 읽고 고쳐서 확정한다.

# worker/concepts/graph.py

- **한 줄 설명**: 개념 사전을 부호 있는 방향 그래프로 읽고, 시작 개념에서 결과 개념까지의 경로·최종 방향(상승 압력 / 하락 압력)·모호성을 코드가 계산한다.
- **입력**: `db/seeds/concepts.csv`, `causal_edges.csv` (`load_graph()`). 테스트나 다른 사전은 `build_graph(names, edges)`로 직접 만든다. CLI는 `--from`, `--to`, `--change up|down`.
- **하는 일**: 연결 `up`은 +1, `down`은 -1로 두고, 같은 개념을 두 번 지나지 않는 모든 경로를 찾아 경로마다 부호를 곱한다. 시작 개념이 줄어드는 사건(`--change down`, 예: 파월 "인하를 서두르지 않겠다" = 인하 기대 ▼)이면 한 번 더 뒤집는다. 모든 경로의 부호가 같으면 그 방향, 다르면 `ambiguous`, 경로가 없으면 `None`. `find_cycle()`은 사전에 순환이 있는지, `ambiguous_pairs()`는 모호한 개념 쌍 전부를 찾는다.
- **출력**: `Effect(start, end, paths=[(경로, ±1)], direction)`. CLI는 인자 없이 돌리면 순환 검사와 모호한 쌍 목록을, `--from/--to`를 주면 경로와 방향을 출력한다.
- **주의할 점**: 기술확정안은 networkx를 적었지만 의존성 추가(A 담당) 없이 표준 라이브러리로 직접 구현했다. 개념 30~50개 규모에서는 모든 경로를 세도 충분히 빠르다. 연결이 "상황에 따라 반대"인 경우(경기 침체 등)는 이 버전에서 따로 다루지 않고, 두 이유를 다른 경로로 나눠 적으면 모호성으로 잡힌다. 2026-10-29 기준 실제 사전(개념 17개, 연결 16개)은 순환 0개, 모호한 쌍 0개.
- **테스트**: `python -m pytest tests/test_graph.py -q` (손계산: 파월 예시 (-1)×(-1)×(+1)에 인하 기대 ▼를 곱해 성장주 하락 압력, X→Y→Z(+)와 X→W→Z(-)는 모호, 실제 사전에서 인하 → 국채 금리 ▼ → 성장주 ▲). 실행 확인: `python -m concepts.graph`, `python -m concepts.graph --from rate_cut --to growth_valuation`.
