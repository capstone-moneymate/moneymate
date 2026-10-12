> **초안 (Claude 작성, 2026-10-12).** 담당자 C가 읽고 고쳐서 확정한다.

# worker/scripts/check_naver_news.py

- **한 줄 설명**: 네이버 검색 API(뉴스, NAVER API HUB)로 기사 20건을 받아 형식을 확인하는 1회성 스크립트.
- **입력**: `.env` 의 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` (NAVER API HUB에서 발급), 검색어(`--query`, 기본: 엔비디아·반도체·기준금리), 모을 건수(`--total`, 기본 20).
- **하는 일**: 검색어마다 최신순으로 받아 `<b>` 태그·HTML 엔티티를 지우고, 제목·요약 길이 통계와 원문 링크 유무, 상위 5건을 출력한다. 카드뉴스 재료로 충분한지는 판단하지 않는다.
- **출력**: 화면 출력 + 레포 루트 `logs/naver_news_sample.json` (커밋하지 않음. .gitignore 에 logs/ 추가 요청 중). DB에는 쓰지 않는다.
- **주의할 점**: 개발자센터 키는 쓸 수 없다(API HUB 이관). 언론사 필드가 없어 `originallink` 도메인으로 추정해야 한다. 기사 본문은 받지도 저장하지도 않는다.
- **테스트**: 1회성 스크립트라 pytest 없음. `cd worker && python scripts/check_naver_news.py` 실행 → 검색어마다 "전체 N건 중 M건"과 통계가 나오는지 확인.
