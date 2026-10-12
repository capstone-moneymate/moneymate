import type { NewsHome } from '@/types/news'

/** 탭1 뉴스 홈 목 데이터. 뉴스·수치는 프로토타입 예시이고, news.ts 연결 후 삭제한다. */
export const newsHomeMock: NewsHome = {
  date: '2026-10-09',
  indices: [
    { code: 'KS11', name: 'KOSPI', value: 2987.42, chgPct: 0.0123, date: '2026-10-08' },
    { code: 'KQ11', name: 'KOSDAQ', value: 842.17, chgPct: -0.0041, date: '2026-10-08' },
    { code: 'IXIC', name: 'NASDAQ', value: 18542.9, chgPct: 0.0087, date: '2026-10-08' },
    { code: 'US500', name: 'S&P 500', value: 5781.33, chgPct: 0.0042, date: '2026-10-08' },
  ],
  cards: [
    {
      id: 'mock-rate-hold',
      type: 2,
      title: '한국은행, 기준금리 4연속 동결',
      summary:
        '물가와 가계부채를 함께 보며 금리를 그대로 뒀어요. 은행주와 기술주가 다르게 반응했어요.',
      theme: '금리',
      press: '연합뉴스',
      url: 'https://www.yna.co.kr/',
      publishedAt: '2026-10-08T01:30:00Z',
      linked13f: false,
      stepCount: 5,
    },
    {
      id: 'mock-hbm4',
      type: 3,
      title: 'HBM4 양산 속도전…SK하이닉스, 엔비디아向 공급 40%↑',
      summary:
        'AI 칩에 들어가는 메모리 공급이 늘어요. 액티브 ETF가 엔비디아를 늘린 이유와 이어져요.',
      theme: 'AI·반도체',
      press: '한국경제',
      url: 'https://www.hankyung.com/',
      publishedAt: '2026-10-08T23:10:00Z',
      linked13f: true,
      stepCount: 3,
    },
    {
      id: 'mock-kospi-3up',
      type: 1,
      title: '코스피, 3거래일 연속 상승 마감',
      summary:
        '외국인 매수가 이어지며 지수가 사흘째 올랐어요. 거래량도 함께 늘었는지 차트로 읽어봐요.',
      theme: '차트 읽기',
      press: '매일경제',
      url: 'https://www.mk.co.kr/',
      publishedAt: '2026-10-08T07:00:00Z',
      linked13f: false,
      stepCount: 4,
    },
  ],
  completedCardIds: ['mock-kospi-3up'],
}
