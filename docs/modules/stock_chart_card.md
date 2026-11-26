> 초안 (Claude 작성, 2026-11-20). 담당자 C가 읽고 고쳐서 확정한다.

# web/src/pages/tab1/StockChartCard.tsx · UpDownQuiz.tsx

- **한 줄 설명:** 탭1 홈 TOP 1 종목의 최근 20거래일 일봉 차트. 지난 카드뉴스가 있던 날 위에 파란 ○, 꾹 누르면 그날 등락률·이유 말풍선.
- **입력:** `NewsHome.stockChart` (`types/news.ts` 의 `StockChart`): ticker·name·market(US/KR)·today·todayCardId·candles(일봉, 어제까지)·notes(날짜별 reason·pastCardId·pastCardTitle). 서버가 `/api/news/home` 의 `stockChart` 로 보낸다(news_api.md, 2026-11-26). 목 모드에서는 `api/mocks/newsHome.ts`.
- **하는 일:** lightweight-charts 로 캔들 + 어제 종가 점선(price line) + 5일선(코드 계산)을 그린다. 오늘은 whitespace 한 칸으로 자리만 잡고 노란 띠로 표시. ○·날짜 눈금·오늘 띠·말풍선은 `timeToCoordinate`/`priceToCoordinate` 로 위치를 재서 HTML 로 얹는다.
- **손 동작:** 350ms 이상 누르면 말풍선, 누른 채 밀면 날짜가 바뀐다. 손을 떼도 말풍선은 남고 짧게 탭하면 닫힌다. 짧은 탭: 오늘 칸 → 오늘 카드(`/news/todayCardId`), ○ → 그날 카드(`/news/pastCardId`). 누르기 전 10px 넘게 움직이면 스크롤로 보고 취소한다(세로 스크롤은 `touch-action: pan-y`).
- **O/X 퀴즈 (UpDownQuiz.tsx):** "오늘 {티커}, 어제보다 올랐을까요?" O 오른다 / X 내린다. 정답은 코드가 정한다: 오늘 종가(`todayClose`) > 어제 종가 → O, < → X, 같으면 둘 다 아님. 마감 전(`todayClose = null`)에는 고른 것만 보여 주고 바꿀 수 있다. 마감 뒤에는 정답·등락률과 "왜 그런지 카드뉴스로 ›". 고른 답은 서버 API 가 없어서 지금은 localStorage(`mm:updown:{ticker}:{today}`)에만 둔다.
- **어떤 종목인가 (출제 규칙, worker 구현 예정):** 하루 카드 중 최소 1장은 차트를 그릴 수 있는 종목 카드. 종목 카드가 있으면 그중 점수 1위 종목. 금리 발표처럼 거시 뉴스만 고른 날은 점수가 가장 낮은 카드를 빼고, 그날 시장 반응이 가장 컸던 종목의 주가·거래량 움직임 카드를 넣는다. 그래서 차트는 항상 하나이고 `todayCardId` 가 그 카드다.
- **출력:** 화면만. 등락률은 (그날 종가 ÷ 전날 종가 − 1), 이유 문장은 notes 의 reason 을 그대로 쓴다(없으면 "이날은 따로 정리한 이유가 없어요.").
- **주의할 점:** 5일선을 첫날부터 그리려면 서버가 candles 를 앞쪽 4일 더 보내야 한다(화면은 마지막 20개만). TradingView 출처 링크는 지우지 않는다. 확대·스크롤은 꺼 두었다(홈 스크롤과 겹침).
- **열린 질문:** O/X 답 서버 저장(탭3 달력·점수에 넣을지), 미국 종목의 '오늘' 기준(KST 아침 마감), (2026-11-26 서버 구현 초안: `/api/news/home` 에 stockChart 추가, reason 은 그 카드 첫 슬라이드 요약, 지난 카드는 대표 자료 종목이 같은 카드 — 담당자 확인 필요).
- **테스트 순서:** 목 모드(`VITE_USE_MOCK=true`)로 홈 → ○ 2개·오늘 띠 확인 → 꾹 눌러 밀기 → ○ 날 말풍선에 "풀어보기" 링크 → 오늘 칸 탭 → 카드뉴스 이동 → O 고르기(안내 문구) → mock 의 todayClose 에 값을 넣고 정답 화면 확인.
