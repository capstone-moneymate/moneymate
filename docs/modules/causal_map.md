> **초안 (Claude 작성, 2026-11-16).** 담당자 B가 읽고 고쳐서 확정한다.

# web/src/pages/tab3/ 인과 지도 (MyPage.tsx, CausalMapView.tsx, causalMapLayout.ts, MapNodes.tsx, mapColors.ts)

- **한 줄 설명**: 탭 3 "나의 인과 지도". 디자인 시안의 가로 나무 모양(뿌리 → 테마 → 개념)을 React Flow(`@xyflow/react`)로 그린다. 테마를 누르면 접고 펴며, 터치로 확대·이동한다. 지금은 목 데이터(#89 React Flow 시험).
- **입력**: `api/mypage.ts`의 `useCausalMap`이 주는 `{ nodes: [{ id, name, theme, correct, total }], edges: [{ from, to, forceDir: 'up' | 'down' }] }` (잠정, `types/causalMap.ts`). `VITE_USE_MOCK`이 `false`면 `GET /api/mypage/map?userId=`를 부르고, 아니면 `api/mocks/causalMap.ts`(테마 6개, 개념 48개, 연결 57개. 사전 17·14 + 가짜)를 쓴다.
- **하는 일**: `causalMapLayout.ts`(순수 함수)가 테마마다 가로 띠를 만들고, 띠 안의 개념을 테마 안 연결의 가장 긴 경로(깊이)로 열을 나눠 원인이 왼쪽·결과가 오른쪽에 오게 놓는다. 접힌 테마는 테마 노드만 남기고(개수 `+N` 표시), 그 테마로 드나드는 연결은 테마 노드로 합친다(같은 쌍은 하나로, 올림·누름이 섞이면 회색 점선). `CausalMapView.tsx`가 그 결과를 React Flow 노드·연결로 바꾸고 범례, + − 전체 버튼, 안내 문구, 개념 정보 패널을 얹는다. 테마를 펴면 그 테마로 화면을 맞추고, 접으면 그 테마 노드를 가운데로 옮긴다.
- **출력**: 화면. 서버에 쓰지 않는다.
- **주의할 점**: 연결 색은 시안대로 올리는 힘 빨강, 누르는 힘 파랑(`mapColors.ts`)이다. 탭 2의 늘림▲·줄임▼와 같은 색이라 ▲▼ 기호는 붙이지 않고 범례로만 설명한다. "복습 필요"는 정답률 50% 미만(`REVIEW_BELOW`, 임시 기준, 한 번도 안 푼 개념은 제외)이다. 숫자는 받은 `correct/total`만 쓴다. 노드 드래그는 껐다(노드 위에서 밀어도 화면이 이동한다). 헤더는 시안대로 뒤로 가기 + 제목이라 공통 `PageHeader`(C 담당) 대신 `MyPage.tsx` 안에 두었다. 개념 48개를 모두 펴면 처음 배율이 약 0.3이라 글자를 읽으려면 확대하거나 테마를 눌러야 하고, 테마 사이 연결이 많이 겹친다.
- **테스트**: web에는 단위 테스트 환경이 없어 브라우저로 확인한다. `cd web && pnpm dev` 후 `/mypage`. 2026-11-16 Chrome 390×844 모바일 터치 에뮬레이션(Playwright)에서 테마 탭 접기·펴기, + − 전체 버튼, 핀치 확대, 한 손가락 이동, 노드 위 드래그 이동, 개념 선택 패널을 확인했다. 콘솔 오류 없음, 가로 스크롤 없음. 실제 휴대폰으로는 확인하지 않았다.
