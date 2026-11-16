> **초안 (Claude 작성, 2026-11-15).** 담당자 B가 읽고 고쳐서 확정한다.

# server: GET /api/mypage/map, GET /api/mypage/review (com.moneymate.mypage)

- **한 줄 설명**: 탭3 마이페이지의 인과 지도(배운 개념 + 거기서 한 걸음 뻗은 사전 연결)와 다시 보는 개념(정답률 낮은 순)을 DB에서 읽어 돌려준다. **읽기 전용.**
- **입력**: `?userId=<UUID>` (필수). 없거나 UUID가 아니면 400 (Spring 기본 응답). 읽는 테이블은 `user_concepts`, `concepts`, `causal_edges`.
- **하는 일** (`MypageService`): ① 배운 개념 = `user_concepts`에서 `total > 0`인 개념 ② 지도의 연결 = `causal_edges` 중 **한쪽 끝이라도** 배운 개념에 닿은 연결 전부. 인과 뼈대는 "이 경로가 정답"이 아니라 "이런 흐름이 가능하다"를 보여 주려는 것이라, 배울수록 가지가 늘어나게 했다 ③ 연결의 반대쪽 끝이 아직 안 배운 개념이면 `learned: false`(correct·total 0) 점으로 함께 내려 준다. 점은 id 순, 연결은 `causal_edges.id` 순 ④ 다시 보는 개념 = `total > 0` 전부(개수 제한 없음). 정렬은 정답률 낮은 순 → 푼 횟수 적은 순("한 번밖에 안 풀어 본 개념을 다시 보세요") → id 순. 정답률은 나눗셈 대신 교차 곱(`a.correct × b.total` 대 `b.correct × a.total`)으로 비교해 소수 오차가 없다.
- **출력**: map `{nodes:[{id,name,theme,correct,total,learned}], edges:[{from,to,forceDir}]}`. `forceDir`는 `up`(올리는 힘) / `down`(누르는 힘). review `{concepts:[{id,name,theme,correct,total,accuracy}]}`. `accuracy`는 소수(0.5 = 50%), 반올림하지 않으니 화면에서 % 표기한다. 기록이 없거나 처음 보는 userId는 200과 빈 배열이다.
- **주의할 점**: `user_concepts`에 쓰는 것은 learning 패키지의 `recordConceptResult`(conventions P17)다. 이 API는 `users`에도 행을 넣지 않는다. 사전 연결이 없는 개념(예: 차트 읽기 `volume_spike`)만 배웠으면 점만 있고 화살표는 없다. node의 `learned` 필드는 이슈 #90에서 정한 것이다. 탭3 화면 타입도 같은 이름으로 맞춘다. 스키마 변경은 없다.
- **테스트**: `cd server; .\gradlew.bat test`. `MypageServiceTest` 7개(DB 없이 가짜 Repository): 한 걸음 이웃(rate_hike 2/3 → 연결 3개, 이웃 3개 learned=false), 배운 개념은 이웃으로 중복되지 않음, 연결 없는 개념은 점만, 기록 없는 사용자는 빈 지도이고 다른 쿼리를 하지 않음, 정렬 손계산(0/1 → 0/3 → 1/4 → 1/3 → 1/2(d) → 1/2(x) → 2/4 → 3/3), total 0 제외, 정답률 소수. 2026-11-15 임시 PostgreSQL 16(001~003 마이그레이션 + 사전 17·14개 + 테스트 사용자)에서 서버를 띄워 확인: rate_hike 2/3·bond_yield 0/1·rate_cut 0/3·volume_spike 0/0 → 점 6개(배움 3, 이웃 3), 연결 7개가 사전 손대조와 같음. review는 bond_yield → rate_cut → rate_hike 순이고 volume_spike는 빠짐. 기록 없음·처음 보는 userId는 빈 배열, userId 없음·`abc`는 400.
