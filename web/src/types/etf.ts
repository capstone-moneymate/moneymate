/**
 * 탭2 액티브 ETF "어제 움직인 종목" API(GET /api/etf/daily, docs/modules/etf_daily_api.md) 응답 타입.
 * 늘림·줄임 판정과 TOP3 는 서버가 한다. 화면은 그대로 보여 준다.
 */

/** ETF 하나와 가장 최근 스냅샷 날짜 */
export interface EtfSnapshot {
  etfCode: string
  snapshotDate: string
}

/** ETF 하나에서 종목 하나의 어제 변화 */
export interface EtfMove {
  etfCode: string
  /** 미국 티커. 변환 못 했으면 null (종목 상세로 이동 불가) */
  ticker: string | null
  /** CUSIP 2~7번째 글자 */
  rawCode: string
  stockName: string | null
  /** 전 거래일 대비, 소수 */
  dayChgPct: number
}

/** 두 ETF 가 함께 늘린 종목 */
export interface TogetherMove {
  ticker: string | null
  rawCode: string
  stockName: string | null
  moves: EtfMove[]
}

export interface EtfDaily {
  /** 늘림·줄임 기준 (0.05 = 5%) */
  threshold: number
  etfs: EtfSnapshot[]
  together: TogetherMove[]
  topIncrease: EtfMove[]
  topDecrease: EtfMove[]
}
