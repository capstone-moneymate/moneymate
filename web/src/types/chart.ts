/** 차트 읽기 하루치. 숫자는 서버가 계산해 내려 주고 화면은 그리기만 한다 */
export interface ChartPoint {
  /** YYYY-MM-DD (거래일) */
  date: string
  close: number
  volume: number
  /** RSI(14). 값이 있는 날이 하나라도 있으면 RSI 칸을 함께 그린다 (worker compute/indicators.py rsi_series) */
  rsi?: number | null
}

export interface ChartData {
  points: ChartPoint[]
  /** 문제에서 말하는 날(예: 발표 날)을 거래량 막대에 표시한다. 정답을 드러내는 날은 넣지 않는다 */
  highlight?: { date: string; label: string }
}
