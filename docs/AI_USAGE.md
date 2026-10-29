 # AI_USAGE.md — AI에게 시킨 일 기록

AI 활용 방식 보고서(8주차)의 재료다. **시킨 일마다 한 줄.** 고친 부분이 중요하다 — AI가 틀린 곳을 사람이 어떻게 고쳤는지가 근거가 된다.

| 날짜 | 담당 | 모듈/파일 | 시킨 일 | AI 결과에서 고친 부분 |
|---|---|---|---|---|
| 2026-10-10 | A | docker-compose.yml, db/migrations/001_init.sql | 문서(기술확정안·분담표) 기반으로 PostgreSQL 설정과 14개 테이블 초안 작성 | 문서의 13개 목록에 없던 cusip_map이 본문에 언급돼 14번째 테이블로 추가됨을 확인하고 유지 |
| 2026-10-10 | A | db/migrations/001_init.sql | 스키마를 문서·conventions.md와 대조해 빠진 것과 어긋난 것을 제안 요청 | 제안 약 25개 중 13F·ETF 계산에 바로 영향을 주는 4개만 선택. 나머지는 해당 주차나 싱크로 보류 |
| 2026-10-10 | A | db/migrations/002_13f_etf_fixes.sql, docs/conventions.md | 선택한 4개를 마이그레이션과 규칙(P12~P15)으로 반영 요청 | unchanged 기준(주식 수가 정확히 같을 때)은 제안대로 수용. 임계값(+N%)은 change_type이 아니라 방향 판정에서만 적용하도록 구분 |
| 2026-10-10 | A | worker/.venv, worker/pyproject.toml | Python 3.12 가상환경 생성·설치 후 pytest, db.py 실행 확인 요청. edgartools 의존성 추가 | edgartools를 내 .venv에만 둘지 pyproject.toml 공통 의존성에 넣을지 제안받고, 공통 의존성으로 넣기로 결정 |
| 2026-10-10 | A | worker/scripts/check_13f_filers.py, docs/findings.md, worker/config.py | edgartools 실제 API 확인 후 큰손 4명 13F 제출 법인 검색 스크립트 작성·실행, 확정 CIK 반영 요청 | 에크먼은 후보(0001336528) 대신 0002026053으로 변경: 함께 보고 법인 목록과 상위 종목을 직접 확인한 뒤 결정. EDGAR_IDENTITY를 한글 이름→영문, naver 메일→gmail로 변경(SEC 403). findings.md 메모 4가지(대신 보고 구조, 11/14 재확인, 틸 보유 8개 싱크 안건, 화면 문구는 법인명 기준) 직접 지시 |
| 2026-10-11 | B | worker/scripts/check_etf_holdings.py, docs/findings.md | pykrx로 TIME·KoAct 구성종목 조회 확인(오늘·9/30·6/30), 확인 스크립트와 findings 정리 요청 | KRX 계정은 간편 로그인 대신 일반 회원가입으로 직접 만들어 사용. AI가 "1CU 기준으로 보인다"고 추정으로 남긴 것을 B가 운용사 사이트에서 직접 확인(TIME 문구, KoAct 설정단위 × 기준가 ≈ 설정현금액)해 확정하고, 자금 유입 보정 제거를 제안. AI가 기억으로 맞춘 "구성종목 코드 = CUSIP 2~7번째 글자"를 B가 Apple(버크셔 13F 원본)·Tesla·NVIDIA CUSIP으로 직접 확인 |
| 2026-10-10 | C | web/src (router.tsx, components/, pages/tab1, api/news.ts·mocks, lib/userId.ts) | 분담표·서비스흐름·UI 수정안 기반으로 390×844 레이아웃, 탭 3개 라우팅, 탭1 뉴스 홈(목 데이터) 작성 | - |
| 2026-10-11 | B | db/seeds/concepts.csv, causal_edges.csv, docs/modules/concept_dictionary.md | 개념 17개와 인과 연결 초안 작성, 금리→예대금리차·동결→성장주 연결의 근거 정리 요청 | AI 요약 2곳에서 원문의 "금리가 오르는/높아지는 시기"를 "높은 수준을 유지하는 시기"로 바꿔 인용한 것을 B가 한국은행 이슈노트 PDF 원문과 대조해 발견 → 동결→예대금리차 화살표 제외(메모로만 남김). 개념 이름을 "예대금리차(잔액 기준)"로 바꾸고 신규취급액 기준은 반대 경향이라는 메모 추가(이슈노트 10쪽 표). "37.3%"는 처음엔 출처 미확인이었으나 PDF 9쪽 표에서 확인. 은행연합회 소비자포털에서 공시 금리 기준(신규·잔액 둘 다 공시)을 직접 확인. 구글 AI 요약, 개인 블로그, 약탈적 저널은 출처에서 제외하고 1차 자료(한국은행 보고서 원문)로 교체. HBM 공급 확대 → 메모리 가격은 B가 TrendForce 자료(2026.5.29, 9.29)를 찾아 초안의 ▼를 ▲로 수정하고, 실적 직접 연결은 가격 경로로 대체하기로 결정 |
| 2026-10-12 | C | worker/.venv | Python 설치와 가상환경·패키지 설치 안내 요청 | 설치 관리자가 기본으로 최신 버전(3.15)을 깔려고 해서, 그 단계를 건너뛰고 팀 기준인 3.12를 직접 골라 설치 |
| 2026-10-12 | C | worker/scripts/check_naver_news.py, docs/findings.md | 네이버 뉴스 API 샘플 20건 확인 스크립트 작성·실행, findings 정리 요청 | AI가 안내한 개발자센터 등록 화면의 "사용 API" 목록에 검색이 없는 것을 C가 직접 확인 → 검색 API가 NAVER API HUB(네이버 클라우드)로 이관된 것을 찾아 주소·인증 헤더를 바꾸게 함 |
| 2026-10-12 | C | worker/scripts/check_claude_call.py, docs/findings.md | Claude 호출 1회 + llm_cost_log 기록 스크립트 작성·실행 요청 | AI가 제안한 키 운영 방식(조직 공유 / 각자 계정) 중, 지금은 C 계정 하나로 쓰고 A는 4주차쯤 조직에 초대해 키를 따로 발급하기로 결정 |
| 2026-10-27 | C | docs/기술확정안.md, docs/개발분담표.md (1차 자료 선별 기준) | 네이버 검색 API 약관 문제 이후 1차 자료(공시·기관 발표) 선별 기준 설계, 논문 근거 정리, 두 문서 반영 요청 | AI가 처음에 근거 없이 정한 사건 급 점수(5·4·3·2점)를 C가 신뢰성이 있냐고 지적해, 논문 기반 기준(비정상 거래량·극단적 수익률 분위, Barber & Odean 2008)으로 바꾸게 함. MacKinlay(1997)의 사건 기간 문장뿐 아니라 다른 논문도 C가 원문을 직접 확인해 근거로 확정함. AI가 제안한 팀원 반자동 카드와 손으로 만드는 감시 종목 명단은 우리가 전문가가 아니라 신뢰성이 없다는 이유로 C가 뺌 |
| 2026-10-29 | A | worker/collectors/filings_13f.py, compute/holdings_change.py, compute/overlap.py, generate/rule_judge.py, common/quarters.py, config.py, tests, docs/modules | 2·3주차 A 몫(13F 수집, 큰손 변화, 겹침 판정, 규칙 채점) 작성과 손계산 pytest, 실제 13F 호출 확인 요청 | - |
