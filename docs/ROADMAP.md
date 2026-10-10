# ROADMAP.md — 주차별 계획 (A 기준 요약, 원본은 docs/분담표.md 5장)

중간고사 주(10/19~10/25)는 비움. 비우는 주에도 ETF 일일 수집이 자동으로 도는지만 확인.

| 주 | 기간 | A | B·C가 A에게 받아야 하는 것 |
|---|---|---|---|
| 1 | 10/9~10/11 | 레포·Docker·스키마·CLAUDE.md·conventions.md, 13F 법인 확인 | 레포 clone, `docker compose up`, worker/db.py·config.py |
| 2 | 10/12~10/18 | 13F 수집(filings_13f.py), 큰손 변화 계산 | server/src/db.ts 뼈대(C가 news.ts 붙일 곳) |
| 쉼 | 10/19~10/25 | ETF 수집 자동 실행 확인만 | |
| 3 | 10/26~11/1 | 겹침 판정 마무리, 규칙 채점(rule_judge.py) | B의 etf_trend 결과를 받아 씀 |
| 4 | 11/2~11/8 | Claude 루브릭 채점, 유형 3 주관식 피드백, judgement.ts | C의 판단해보기 화면이 /api/judgement 호출 |
| 5 | 11/9~11/15 | 탭2 API·메인·카드 ①, 3분기 13F 갱신(11/14 마감) | C의 유형 3 화면이 종목 상세로 이어짐 |
| 6 | 11/16~11/22 | 탭2 카드 ②③, 개념↔티커 매핑, TradingAgents 1주 시험 | C의 reasons.py, B의 개념 사전 연결 |
| 7 | 11/23~11/29 | 답안 40개 LLM 채점 제공, 11/27 기능 동결 | C가 κ 계산 |
| 8 | 11/30~12/4 | 리허설, 발표 자료 | |
