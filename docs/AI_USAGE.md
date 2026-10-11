# AI_USAGE.md — AI에게 시킨 일 기록

AI 활용 방식 보고서(8주차)의 재료다. **시킨 일마다 한 줄.** 고친 부분이 중요하다 — AI가 틀린 곳을 사람이 어떻게 고쳤는지가 근거가 된다.

| 날짜 | 담당 | 모듈/파일 | 시킨 일 | AI 결과에서 고친 부분 |
|---|---|---|---|---|
| 2026-10-10 | A | docker-compose.yml, db/migrations/001_init.sql | 문서(기술확정안·분담표) 기반으로 PostgreSQL 설정과 14개 테이블 초안 작성 | 문서의 13개 목록에 없던 cusip_map이 본문에 언급돼 14번째 테이블로 추가됨을 확인하고 유지 |
| 2026-10-10 | A | db/migrations/001_init.sql | 스키마를 문서·conventions.md와 대조해 빠진 것과 어긋난 것을 제안 요청 | 제안 약 25개 중 13F·ETF 계산에 바로 영향을 주는 4개만 선택. 나머지는 해당 주차나 싱크로 보류 |
| 2026-10-10 | A | db/migrations/002_13f_etf_fixes.sql, docs/conventions.md | 선택한 4개를 마이그레이션과 규칙(P12~P15)으로 반영 요청 | unchanged 기준(주식 수가 정확히 같을 때)은 제안대로 수용. 임계값(+N%)은 change_type이 아니라 방향 판정에서만 적용하도록 구분 |
| 2026-10-10 | A | worker/.venv, worker/pyproject.toml | Python 3.12 가상환경 생성·설치 후 pytest, db.py 실행 확인 요청. edgartools 의존성 추가 | edgartools를 내 .venv에만 둘지 pyproject.toml 공통 의존성에 넣을지 제안받고, 공통 의존성으로 넣기로 결정 |
| 2026-10-10 | A | worker/scripts/check_13f_filers.py, docs/findings.md, worker/config.py | edgartools 실제 API 확인 후 큰손 4명 13F 제출 법인 검색 스크립트 작성·실행, 확정 CIK 반영 요청 | 에크먼은 후보(0001336528) 대신 0002026053으로 변경: 함께 보고 법인 목록과 상위 종목을 직접 확인한 뒤 결정. EDGAR_IDENTITY를 한글 이름→영문, naver 메일→gmail로 변경(SEC 403). findings.md 메모 4가지(대신 보고 구조, 11/14 재확인, 틸 보유 8개 싱크 안건, 화면 문구는 법인명 기준) 직접 지시 |
| 2026-10-11 | B | worker/scripts/check_etf_holdings.py, docs/findings.md | pykrx로 TIME·KoAct 구성종목 조회 확인(오늘·9/30·6/30), 확인 스크립트와 findings 정리 요청 | KRX 계정은 간편 로그인 대신 일반 회원가입으로 직접 만들어 사용. AI가 "1CU 기준으로 보인다"고 추정으로 남긴 것을 B가 운용사 사이트에서 직접 확인(TIME 문구, KoAct 설정단위 × 기준가 ≈ 설정현금액)해 확정하고, 자금 유입 보정 제거를 제안 |
