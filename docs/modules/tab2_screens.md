> **초안 (Claude 작성, 2026-11-16).** 담당자 A가 읽고 고쳐서 확정한다.

# web: 탭2 메인·종목 상세 (web/src/pages/tab2)

- **한 줄 설명**: `/etf` 메인(13F 공시 겹침 / 액티브 ETF 어제 변화 스위치)과 `/etf/:ticker` 종목 상세(헤더 + 카드 ① 무엇이 바뀌었나, 카드 ②③은 자리만 #101).
- **입력**: `api/overlap.ts`의 `useOverlaps`(GET /api/overlaps), `useStockOverlap`(GET /api/stocks/:ticker), `useEtfDaily`(GET /api/etf/daily). `VITE_USE_MOCK`이 `false`가 아니면 `api/mocks/overlap.ts`·`etfDaily.ts`(서버 통합 테스트 fixture와 같은 값).
- **하는 일**: 영어 상수·코드를 `labels.ts` 한 곳에서 한글로 바꾼다(changeType: 새로 담음/늘림/줄임/모두 정리/변화 없음, direction: 같은 방향/방향 다름/비교 보류, 큰손 4명 법인명+사람, ETF TIME·KoAct). 변화율은 C의 `ChangeRate`(▲▼)로 보여 준다. 스위치 선택은 `?view=etf`로 주소에 남아 상세에서 뒤로 와도 유지된다.
- **메인 13F**: 겹친 종목 카드(티커·이름, 큰손별 변화, 보유 ETF, 방향 칩 개수) → 누르면 상세. 기준일(13F 분기 말)과 공시 후 경과일(가장 늦은 공시일 기준, KST 오늘). 하단 "변동성 TOP2"는 자리만. **"N명 늘림"은 넣지 않았다** (서버가 판정값을 저장하지 않아 화면이 세면 worker 5% 기준과 어긋남. 004 `big_dir` 이후 추가).
- **메인 ETF**: 함께 늘림 / 가장 많이 늘림 / 가장 많이 줄임 (서버가 고른 그대로). 행은 누를 수 없다(겹침에 없는 종목은 상세가 없음).
- **상세 카드 ①**: 큰손 4명(응답에 없으면 "기록 없음"), ETF 추세, "어제만 보면", (큰손 × ETF) 방향 비교, 방향 다름이 있으면 시점 차이 설명. 섹터·성격 태그, 회사 소개, "추세와 반대로 움직인 이유"는 데이터가 없어 비워 둠.
- **상태**: 로딩 "불러오는 중…", 오류 문구, 빈 결과 안내, 상세 404는 "겹친 종목이 아니에요". 뒤로는 앱 안에서 왔으면 이전 화면, 주소로 바로 왔으면 `/etf`.
- **주의할 점**: 터치 영역은 스위치·뒤로 44px, 목록 행 48px 이상. C의 `PageHeader` 알림 버튼은 40px라(공통 컴포넌트라 고치지 않음) C에게 44px 요청 후보. 큰손·ETF 이름은 worker/config.py·findings.md와 손으로 맞춘 상수다.
- **테스트**: `cd web; pnpm exec tsc -b; pnpm exec eslint src; pnpm run build`. 화면 흐름은 390×844 headless Chrome으로 메인 → NVDA 카드 → 뒤로 → ETF 스위치 → `/etf/AAPL`(404) → 뒤로(`/etf`)를 눌러 확인(가로 스크롤 없음).
