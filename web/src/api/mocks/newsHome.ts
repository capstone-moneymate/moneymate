import type { NewsHome } from '@/types/news'

/** 탭1 뉴스 홈 목 데이터. 자료·수치는 프로토타입 예시이고, 뉴스 API 연결 후 삭제한다. */
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
      sourceName: '한국은행',
      sourceUrl: 'https://www.bok.or.kr/',
      sourcePublishedAt: '2026-10-08T01:30:00Z',
      stepCount: 5,
    },
    {
      id: 'mock-hbm4',
      type: 3,
      title: 'SK하이닉스, HBM 단일판매·공급계약 체결',
      summary:
        'AI 칩에 들어가는 메모리(HBM) 공급 계약을 공시했어요. 액티브 ETF가 엔비디아를 늘린 이유와 이어져요.',
      theme: 'AI·반도체',
      sourceName: 'DART · SK하이닉스',
      sourceUrl: 'https://dart.fss.or.kr/',
      sourcePublishedAt: '2026-10-08T07:40:00Z',
      stepCount: 3,
    },
    {
      id: 'mock-kospi-3up',
      type: 1,
      title: '코스피, 3거래일 연속 상승 마감',
      summary: '지수가 사흘째 올랐어요. 거래량도 함께 늘었는지 차트로 읽어봐요.',
      theme: '차트 읽기',
      sourceName: 'KRX 시세',
      sourceUrl: 'https://data.krx.co.kr/',
      sourcePublishedAt: '2026-10-08T06:30:00Z',
      stepCount: 4,
    },
  ],
  completedCardIds: ['mock-kospi-3up'],
}
