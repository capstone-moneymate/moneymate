/**
 * 탭2 겹침 API(#97, docs/modules/overlap_api.md) 응답 타입.
 * 변화율은 소수(0.05 = +5%), 날짜는 YYYY-MM-DD. 영어 상수는 화면이 한글로 바꾼다 (pages/tab2/labels.ts).
 */

/** 큰손 13F 변화 종류 ← holdings_13f.change_type */
export type ChangeType = 'new' | 'increase' | 'decrease' | 'exit' | 'unchanged'

/** 큰손과 ETF 의 방향 비교 ← overlap_results.direction */
export type Direction = 'same' | 'diff' | 'none'

/** 큰손 한 명의 13F 변화 */
export interface FilerChange {
  /** buffett / druckenmiller / thiel / ackman */
  filerKey: string
  /** 13F 제출 법인명 */
  filerName: string | null
  changeType: ChangeType | null
  /** 직전 분기 대비. 신규 편입(new)이면 null */
  chgPct: number | null
  /** 13F 분기 말 */
  periodEnd: string
  /** 공시일 */
  filedAt: string | null
}

/** 액티브 ETF 하나의 추세·어제 변화 */
export interface EtfChange {
  etfCode: string
  /** 비교에 쓴 ETF 최신 스냅샷 날짜 */
  snapshotDate: string
  /** 13F 분기 말 이후 추세. ETF 가 새로 담았으면 null */
  trendChgPct: number | null
  /** 전 거래일 대비 ("어제만 보면"). 없으면 null */
  dayChgPct: number | null
}

/** (큰손, ETF) 한 쌍의 방향 */
export interface DirectionPair {
  filerKey: string
  etfCode: string
  direction: Direction
}

/** 종목 하나의 겹침. 목록 한 항목이자 GET /api/stocks/{ticker} 응답 */
export interface StockOverlap {
  calcDate: string
  ticker: string
  issuerName: string | null
  etfStockName: string | null
  filers: FilerChange[]
  etfs: EtfChange[]
  pairs: DirectionPair[]
}

/** GET /api/overlaps. 겹침 결과가 없으면 calcDate 는 null */
export interface OverlapList {
  calcDate: string | null
  stocks: StockOverlap[]
}

// ---------------------------------------------------------------- 종목 상세 카드 ②③ (#101)

/** 카드 ② 인과 경로의 개념 하나. learned 는 이 사용자가 배운 개념인지 */
export interface PathConcept {
  id: string
  name: string
  learned: boolean
}

/** 카드 ② 근거 자료. no 는 C 가 붙인 번호이고 화면이 1부터 다시 매긴다. 기사 본문은 없다 */
export interface ReasonEvidence {
  no: number | null
  publishedDate: string
  title: string
  /** 발표 기관·언론사. 없을 수 있다 */
  issuerName: string | null
  url: string
}

/** 카드 ② 이유 하나 */
export interface StockReason {
  title: string
  body: string
  /** 원인 → … → 결과 (B 의 개념 사전 경로) */
  path: PathConcept[]
  /** 시작 개념이 커질 때 끝 개념이 받는 힘: up(▲ 올리는 힘) / down(▼ 누르는 힘) */
  direction: 'up' | 'down'
  /** 경로에 배운 개념이 있으면 true ("내 지도에 있어요") */
  inMyMap: boolean
  evidence: ReasonEvidence[]
  /**
   * 양쪽 이유일 때 설명하는 쪽: big(큰손, 분기 말 이전 근거) / etf(ETF, 분기 말 이후 근거).
   * 큰손과 ETF 가 반대로 움직인 종목만 있고, 그 밖은 null. 이 쪽의 direction 은 그 쪽 변화와 같다 (worker 검사)
   */
  side: 'big' | 'etf' | null
}

/** 카드 ③ 기준일 이후 주가. returnPct 는 퍼센트 값 (12.5 = 12.5%) */
export interface NowPrice {
  fromDate: string
  fromClose: number
  toDate: string
  toClose: number
  returnPct: number
}

/** 카드 ③ 기준일 뒤 자료. numbers 는 공시에서 코드가 뽑은 값 */
export interface NowSource {
  publishedDate: string
  title: string
  url: string
  numbers: Record<string, number | string>
}

/** 카드 ③ 이유 경로 개념 중 오늘 탭 1 카드가 다룬 개념 */
export interface NowLinked {
  conceptId: string
  name: string
  reasonTitle: string
}

/** 카드 ③ 지금은. text 는 문장 검사를 못 넘으면 null (사실만 보여 준다) */
export interface StockNow {
  baseDate: string
  price: NowPrice | null
  laterSources: NowSource[]
  linked: NowLinked[]
  text: string | null
}

/** 카드 ②③ (stock_reasons published 최근 분기 한 줄) */
export interface StockReasons {
  bigPeriodEnd: string
  direction: Direction
  change: 'up' | 'down'
  headline: string
  reasons: StockReason[]
  /** 카드 ③ 이 아직 없으면 null */
  now: StockNow | null
}

/** "내 지도에 있어요" 개념 (#100 매핑) */
export interface MyMapConcept {
  id: string
  name: string
  theme: string
}

/** GET /api/stocks/{ticker}?userId= 응답 */
export interface StockDetail extends StockOverlap {
  /** published 이유가 없으면 null (화면은 대체 문구) */
  reasons: StockReasons | null
  /** reasons 가 null 이고 가장 최근 분기 이유가 검사에서 전부 버려졌으면 true (#164). 화면은 "찾지 못했어요" 고정 문구 */
  reasonsRejected: boolean
  /** 이 종목과 연결된 개념 중 배운 것 */
  myConcepts: MyMapConcept[]
}
