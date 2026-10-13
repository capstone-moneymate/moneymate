/** 탭1 뉴스 홈에서 쓰는 타입. 서버 news.ts 응답도 이 모양에 맞춘다. */

/** 주요 지수 한 칸 (KOSPI, KOSDAQ, NASDAQ, S&P 500) */
export interface MarketIndex {
  code: string
  name: string
  value: number
  /** 전 거래일 대비 변화율, 소수 (0.012 = +1.2%) */
  chgPct: number
  /** 그 시장의 거래일 (YYYY-MM-DD) */
  date: string
}

/** 뉴스 유형. 1: 인과 뼈대 없음, 2: 인과 뼈대 있음, 3: 액티브 ETF 종목 연결 */
export type NewsType = 1 | 2 | 3

/** 홈에 보이는 오늘의 카드뉴스 한 건 */
export interface NewsCardSummary {
  id: string
  type: NewsType
  title: string
  /** 한 줄 요약 (Claude가 쓴 요약. 기사 본문은 저장하지 않음) */
  summary: string
  /** 테마 태그 (금리, AI·반도체, 차트 읽기 …) */
  theme: string
  /** 원문 언론사 */
  press: string
  /** 원문 링크 */
  url: string
  /** 발행 시각 (ISO, UTC) */
  publishedAt: string
  /** "13F·ETF 연결" 배지 */
  linked13f: boolean
  /** 학습 단계 수 (유형마다 다름) */
  stepCount: number
}

export interface NewsHome {
  /** 카드뉴스 기준일 (KST, YYYY-MM-DD) */
  date: string
  indices: MarketIndex[]
  cards: NewsCardSummary[]
  /** 이 사용자가 학습을 끝낸 카드 id */
  completedCardIds: string[]
}
