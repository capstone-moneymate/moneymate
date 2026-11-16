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
