> **초안 (Claude 작성, 2026-10-10).** 담당자 A가 읽고 고쳐서 확정한다.

# worker/scripts/check_13f_filers.py

- **한 줄 설명**: 큰손 4명의 13F 제출 법인 후보를 SEC EDGAR에서 이름으로 찾아 전부 출력하는 1회성 확인 스크립트.
- **입력**: `.env` 의 `EDGAR_IDENTITY` (영문 이름 + naver 아닌 메일), 스크립트 안의 검색어 `SEARCH_TERMS` (findings.md 후보 법인명 기준).
- **하는 일**: SEC 전체 법인명 목록(`get_cik_lookup_data`)에서 검색어가 들어간 법인을 모두 찾고, 법인마다 최근 13F-HR 기간·공시일·보유 종목 수·13F-NT 이력을 조회한다. 어느 법인이 맞는지는 판단하지 않는다.
- **출력**: 화면 출력만 (DB·파일에 쓰지 않음). 13F-HR을 낸 법인이 위로 정렬.
- **주의할 점**: `find_company()` 는 상장사 티커 목록만 검색해 운용사가 빠지므로 쓰지 않는다. 한글 이름·naver 메일이면 안내 후 종료. 확정 결과는 사람이 고른 뒤 docs/findings.md, worker/config.py `FILERS` 에 반영.
- **테스트**: 1회성 스크립트라 pytest 없음. 확인 방법은 `cd worker && python scripts/check_13f_filers.py` 실행 → 4명 모두 2026-06-30 13F-HR 법인이 나오는지.
