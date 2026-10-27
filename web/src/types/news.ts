/**
 * 탭1 뉴스 홈에서 쓰는 타입. 서버 뉴스 API(Spring Boot) 응답도 이 모양에 맞춘다.
 * 각 필드 주석의 "← "는 서버가 값을 가져올 테이블·컬럼이다.
 */

/** 주요 지수 한 칸 (KOSPI, KOSDAQ, NASDAQ, S&P 500) ← prices */
export interface MarketIndex {
  code: string
  name: string
  value: number
  /** 전 거래일 대비 변화율, 소수 (0.012 = +1.2%) */
  chgPct: number
  /** 그 시장의 거래일 (YYYY-MM-DD) */
  date: string
}

/** 카드 유형 ← cards.card_type. 1: 인과 뼈대 없음, 2: 인과 뼈대 있음, 3: 액티브 ETF 종목 연결 */
export type CardType = 1 | 2 | 3

/** 홈에 보이는 오늘의 카드 한 건 */
export interface NewsCardSummary {
  /** ← cards.id */
  id: string
  /** ← cards.card_type. 3이면 "13F·ETF 연결" 배지를 보여준다 */
  type: CardType
  /** ← cards.title */
  title: string
  /** 한 줄 요약 ← cards.slides 첫 장("무슨 일이 있었나요?")의 본문을 서버가 잘라 준다 */
  summary: string
  /** 테마 태그(금리, AI·반도체, 차트 읽기 …) ← cards.start_concept로 concepts.theme 조인. 시작 개념이 없으면 null */
  theme: string | null
  /** 1차 자료 출처 이름 (예: 한국은행, DART · SK하이닉스) ← 1차 자료 테이블(스키마 확정 전) */
  sourceName: string
  /** 1차 자료 원문 링크 ← cards.source_links 첫 번째 */
  sourceUrl: string
  /**
   * 1차 자료가 발표된 시각 (ISO, UTC). 화면에서 KST로 표시.
   * cards.published_at(팀 확인 후 게시된 시각)과 다르다.
   */
  sourcePublishedAt: string
  /** 학습 단계 수 ← 그 카드의 steps 개수 */
  stepCount: number
}

export interface NewsHome {
  /** 카드 기준일 (KST, YYYY-MM-DD) */
  date: string
  indices: MarketIndex[]
  cards: NewsCardSummary[]
  /** 이 사용자가 학습을 끝낸 카드 id ← user_answers */
  completedCardIds: string[]
}
