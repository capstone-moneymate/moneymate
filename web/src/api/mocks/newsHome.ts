import type { Candle, NewsHome, PastNews, StockChart } from '@/types/news'

/** 목 종목 차트: 2026-11-19 까지 20거래일(주말 제외) NVDA 모양의 예시 값. 실제 시세가 아니다 */
const mockCandles = (): Candle[] => {
  const closes = [
    181.2, 180.4, 182.9, 186.1, 192.8, 191.5, 188.7, 187.9, 190.6, 191.9, 187.3, 184.6, 190.1,
    194.4, 192.2, 190.8, 189.6, 188.4, 186.4, 189.6,
  ]
  const dates: string[] = []
  const day = new Date(Date.UTC(2026, 10, 19))
  while (dates.length < closes.length) {
    const dow = day.getUTCDay()
    if (dow !== 0 && dow !== 6) dates.unshift(day.toISOString().slice(0, 10))
    day.setUTCDate(day.getUTCDate() - 1)
  }
  return closes.map((close, i) => {
    const open = i === 0 ? close - 0.8 : closes[i - 1] + (i % 3 === 0 ? 0.6 : -0.4)
    return {
      date: dates[i],
      open,
      high: Math.max(open, close) + 1.1 + (i % 4) * 0.3,
      low: Math.min(open, close) - 1.2 - (i % 3) * 0.3,
      close,
    }
  })
}

const candles = mockCandles()

const stockChart: StockChart = {
  ticker: 'NVDA',
  name: '엔비디아',
  market: 'US',
  today: '2026-11-20',
  todayCardId: 'mock-hbm4',
  todayClose: null, // 마감 뒤 화면을 보려면 191.5 같은 값을 넣는다
  candles,
  notes: [
    {
      date: candles[4].date,
      reason: '데이터센터 매출 전망을 올려 잡으면서 하루 만에 3% 넘게 뛰었어요.',
      pastCardId: 'mock-hbm4',
      pastCardTitle: 'SK하이닉스, HBM 단일판매·공급계약 체결',
    },
    {
      date: candles[10].date,
      reason: '금리 결정을 앞두고 기술주 전반에 차익 매물이 나왔어요.',
      pastCardId: null,
      pastCardTitle: null,
    },
    {
      date: candles[13].date,
      reason: '연속 상승 뒤 윗꼬리, 고점에서 차익 매물이 나왔어요.',
      pastCardId: 'mock-rate-hold',
      pastCardTitle: '한국은행, 기준금리 4연속 동결',
    },
    {
      date: candles[19].date,
      reason: 'HBM4 공급 소식에 다시 사려는 사람이 늘었어요.',
      pastCardId: null,
      pastCardTitle: null,
    },
  ],
}

/** 탭1 뉴스 홈 목 데이터. 자료·수치는 프로토타입 예시이고, 뉴스 API 연결 후 삭제한다. */
export const newsHomeMock: NewsHome = {
  date: '2026-10-09',
  indices: [
    { code: 'KS11', name: 'KOSPI', value: 2987.42, chgPct: 0.0123, date: '2026-10-08' },
    { code: 'KQ11', name: 'KOSDAQ', value: 842.17, chgPct: -0.0041, date: '2026-10-08' },
    { code: 'IXIC', name: 'NASDAQ', value: 18542.9, chgPct: 0.0087, date: '2026-10-08' },
    { code: 'US500', name: 'S&P 500', value: 5781.33, chgPct: 0.0042, date: '2026-10-08' },
  ],
  stockChart,
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

/**
 * 지난 뉴스 목 데이터. 목에는 카드 상세가 세 건뿐이라 지난 카드도 그 세 건을 가리킨다 (제목은 그 카드의 것).
 * 뉴스 API 연결 후 삭제한다.
 */
export const pastNewsMock: PastNews = {
  cards: [
    { date: '2026-10-07', card: newsHomeMock.cards[1] },
    { date: '2026-10-06', card: newsHomeMock.cards[2] },
    { date: '2026-10-02', card: newsHomeMock.cards[0] },
  ],
  completedCardIds: ['mock-kospi-3up'],
}
