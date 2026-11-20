/**
 * 탭1 뉴스 홈에서 쓰는 타입. 서버 뉴스 API(Spring Boot) 응답도 이 모양에 맞춘다.
 * 각 필드 주석의 "← "는 서버가 값을 가져올 테이블·컬럼이다.
 */

/** 주요 지수 한 칸 (KOSPI, KOSDAQ, NASDAQ, S&P 500) ← prices */
export interface MarketIndex {
  code: string
  name: string
  value: number
  /** 전 거래일 대비 변화율, 소수 (0.012 = +1.2%). 전 거래일 종가가 없으면 null */
  chgPct: number | null
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
   * cards.published_at(팀 확인 후 게시된 시각)과 다르다. 시각을 모르는 DART 는 그 날짜 0시 KST,
   * 1차 자료가 없으면 null.
   */
  sourcePublishedAt: string | null
  /** 학습 단계 수 ← 그 카드의 steps 개수 */
  stepCount: number
}

/** 종목 차트의 일봉 하나 ← prices */
export interface Candle {
  /** 그 시장 거래일 (YYYY-MM-DD) */
  date: string
  open: number
  high: number
  low: number
  close: number
}

/**
 * 차트에서 날짜 하나에 붙는 설명.
 * reason 은 꾹 눌렀을 때 말풍선에 나오는 한두 문장, pastCardId 가 있으면 그날 위에 ○ 를 띄운다.
 */
export interface StockChartNote {
  date: string
  /** 그날 왜 움직였는지 한두 문장. 없으면 null (말풍선에 등락률만 보여 준다) */
  reason: string | null
  /** 그날 나왔던 카드뉴스 → 지난 뉴스로 풀 수 있다 */
  pastCardId: string | null
  pastCardTitle: string | null
}

/**
 * 탭1 홈 종목 차트 (최근 20거래일 일봉). 차트는 항상 하나 나온다.
 * 어떤 종목인지 (worker 출제 규칙, 하루 카드 중 최소 1장은 차트를 그릴 수 있는 종목 카드):
 *  - 그날 카드에 종목 카드가 있으면 그중 점수 1위 종목
 *  - 금리 발표처럼 종목 없는 거시 뉴스만 고른 날은 점수가 가장 낮은 카드를 빼고,
 *    그날 시장 반응이 가장 컸던 종목의 주가·거래량 움직임으로 만든 카드를 넣는다 → 그 종목
 * todayCardId 는 그 카드. 차트(오늘 칸)를 누르면 이 카드뉴스로 간다.
 * candles 는 어제까지(오늘은 마감 전이면 빈 칸 + O/X 퀴즈).
 * 5일선을 첫날부터 그리려고 앞쪽 4일을 더 보내도 되고, 화면은 마지막 20개만 그린다.
 */
export interface StockChart {
  /** NVDA / 000660.KS */
  ticker: string
  /** 엔비디아 */
  name: string
  /** US → $ 소수 둘째 자리, KR → 원 */
  market: 'US' | 'KR'
  /** 오늘 (그 시장 기준, 아직 마감 전) */
  today: string
  /** 오늘 칸을 누르면 가는 오늘의 카드뉴스 */
  todayCardId: string | null
  /** 오늘 종가. 장 마감 전이면 null → O/X 퀴즈 정답은 마감 뒤에 (오늘 종가 vs 어제 종가) */
  todayClose: number | null
  candles: Candle[]
  notes: StockChartNote[]
}

export interface NewsHome {
  /** 카드 기준일 (KST, YYYY-MM-DD) */
  date: string
  /** 종목 차트. 서버가 아직 안 보내면 없음(undefined) */
  stockChart?: StockChart | null
  indices: MarketIndex[]
  cards: NewsCardSummary[]
  /** 이 사용자가 학습을 끝낸 카드 id ← user_answers */
  completedCardIds: string[]
}
