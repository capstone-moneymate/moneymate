import type { CausalMap, ForceDir, MapEdge, MapNode } from '@/types/causalMap'

/**
 * 탭3 인과 지도 목 데이터 (React Flow 시험용, #89).
 * - "사전" 표시는 db/seeds/concepts.csv·causal_edges.csv 에 있는 개념·연결(17개·14개)을 옮긴 것이다.
 * - "가짜" 표시는 개념 30~50개에서 확대·이동·접기를 시험하려고 지어낸 것이다. 사전에 없고, 인과 설명의 근거도 아니다.
 * - 맞힌 횟수·푼 횟수(correct/total)는 모두 가짜다. 0/0 은 아직 안 배운 개념(learned=false)이다.
 * - 테마 6개는 개념 30~50개를 가정한 시험용이다.
 * VITE_USE_MOCK 이 'false' 가 아닐 때(서버 없이 화면 볼 때)만 쓴다.
 */

type NodeRow = [id: string, name: string, theme: string, correct: number, total: number]
type EdgeRow = [from: string, to: string, forceDir: ForceDir]

const NODE_ROWS: NodeRow[] = [
  // 금리 — 사전 7개
  ['rate_hike', '기준금리 인상', '금리', 3, 4],
  ['rate_cut', '기준금리 인하', '금리', 2, 3],
  ['rate_hold', '기준금리 동결', '금리', 4, 5],
  ['inflation', '물가 상승', '금리', 1, 3],
  ['bond_yield', '국채 금리', '금리', 2, 2],
  ['bank_margin', '은행 예대금리차(잔액 기준)', '금리', 1, 2],
  ['growth_valuation', '성장주 가치평가', '금리', 0, 0],
  // 금리 — 가짜 2개
  ['deposit_rate', '예금 금리', '금리', 2, 2],
  ['interest_burden', '가계 이자 부담', '금리', 1, 1],

  // AI·반도체 — 사전 6개
  ['ai_investment', 'AI 데이터센터 투자', 'AI·반도체', 3, 3],
  ['gpu_demand', 'AI 반도체 수요', 'AI·반도체', 2, 4],
  ['hbm_supply', 'HBM 공급 확대', 'AI·반도체', 1, 2],
  ['hbm_demand', 'HBM 수요', 'AI·반도체', 3, 4],
  ['memory_price', '범용 메모리(D램) 가격', 'AI·반도체', 0, 0],
  ['semi_earnings', '반도체 기업 실적', 'AI·반도체', 2, 3],
  // AI·반도체 — 가짜 3개
  ['foundry_util', '파운드리 가동률', 'AI·반도체', 1, 2],
  ['semi_capex', '반도체 설비투자', 'AI·반도체', 0, 0],
  ['semi_export', '반도체 수출', 'AI·반도체', 2, 3],

  // 차트 읽기 — 사전 4개
  ['volume_spike', '거래량 급증', '차트 읽기', 4, 4],
  ['rsi_overbought', 'RSI 과매수', '차트 읽기', 1, 3],
  ['ma_breakout', '이동평균선 돌파', '차트 읽기', 2, 2],
  ['consecutive_rise', '연속 상승', '차트 읽기', 3, 3],
  // 차트 읽기 — 가짜 4개
  ['volume_drop', '거래량 감소', '차트 읽기', 1, 1],
  ['rsi_oversold', 'RSI 과매도', '차트 읽기', 0, 1],
  ['ma_breakdown', '이동평균선 이탈', '차트 읽기', 1, 2],
  ['consecutive_fall', '연속 하락', '차트 읽기', 2, 2],

  // 환율 — 가짜 8개
  ['us_rate', '미국 기준금리 인상', '환율', 2, 3],
  ['dollar_index', '달러 강세', '환율', 1, 2],
  ['rate_gap', '한미 금리 차 확대', '환율', 0, 1],
  ['foreign_outflow', '외국인 자금 유출', '환율', 1, 2],
  ['usd_krw', '원·달러 환율 상승', '환율', 3, 4],
  ['import_price', '수입 물가', '환율', 1, 1],
  ['exporter_earnings', '수출 기업 이익', '환율', 2, 2],
  ['fx_reserve', '외환보유액', '환율', 0, 0],

  // 유가·에너지 — 가짜 7개
  ['opec_cut', '산유국 감산', '유가·에너지', 1, 1],
  ['oil_price', '국제 유가', '유가·에너지', 2, 3],
  ['refining_margin', '정제 마진', '유가·에너지', 1, 2],
  ['airline_cost', '항공사 연료비', '유가·에너지', 1, 1],
  ['energy_earnings', '에너지 기업 실적', '유가·에너지', 0, 1],
  ['gasoline_price', '휘발유 가격', '유가·에너지', 2, 2],
  ['ev_demand', '전기차 수요', '유가·에너지', 0, 0],

  // 경기·고용 — 가짜 7개
  ['employment', '고용 증가', '경기·고용', 2, 2],
  ['unemployment', '실업률 상승', '경기·고용', 1, 2],
  ['consumer_spending', '소비 지출', '경기·고용', 1, 3],
  ['retail_sales', '소매 판매', '경기·고용', 1, 1],
  ['gdp_growth', '경제 성장률', '경기·고용', 2, 3],
  ['recession_fear', '경기 침체 우려', '경기·고용', 0, 2],
  ['corp_earnings', '기업 이익 전반', '경기·고용', 0, 0],
]

const EDGE_ROWS: EdgeRow[] = [
  // 사전 14개
  ['inflation', 'rate_hike', 'up'],
  ['inflation', 'rate_cut', 'down'],
  ['rate_hike', 'bond_yield', 'up'],
  ['rate_cut', 'bond_yield', 'down'],
  ['rate_hike', 'bank_margin', 'up'],
  ['rate_cut', 'bank_margin', 'down'],
  ['rate_hold', 'growth_valuation', 'down'],
  ['bond_yield', 'growth_valuation', 'down'],
  ['ai_investment', 'gpu_demand', 'up'],
  ['gpu_demand', 'hbm_demand', 'up'],
  ['hbm_demand', 'memory_price', 'up'],
  ['hbm_supply', 'memory_price', 'up'],
  ['memory_price', 'semi_earnings', 'up'],
  ['gpu_demand', 'semi_earnings', 'up'],

  // 가짜 — 테마 안
  ['rate_hike', 'deposit_rate', 'up'],
  ['bond_yield', 'interest_burden', 'up'],
  ['gpu_demand', 'foundry_util', 'up'],
  ['foundry_util', 'semi_earnings', 'up'],
  ['semi_earnings', 'semi_capex', 'up'],
  ['memory_price', 'semi_export', 'up'],
  ['volume_spike', 'ma_breakout', 'up'],
  ['consecutive_rise', 'rsi_overbought', 'up'],
  ['volume_drop', 'ma_breakout', 'down'],
  ['ma_breakdown', 'consecutive_fall', 'up'],
  ['consecutive_fall', 'rsi_oversold', 'up'],
  ['consecutive_rise', 'rsi_oversold', 'down'],
  ['us_rate', 'dollar_index', 'up'],
  ['us_rate', 'rate_gap', 'up'],
  ['rate_gap', 'foreign_outflow', 'up'],
  ['dollar_index', 'usd_krw', 'up'],
  ['foreign_outflow', 'usd_krw', 'up'],
  ['usd_krw', 'import_price', 'up'],
  ['usd_krw', 'exporter_earnings', 'up'],
  ['usd_krw', 'fx_reserve', 'down'],
  ['opec_cut', 'oil_price', 'up'],
  ['oil_price', 'refining_margin', 'up'],
  ['oil_price', 'airline_cost', 'up'],
  ['oil_price', 'energy_earnings', 'up'],
  ['oil_price', 'gasoline_price', 'up'],
  ['gasoline_price', 'ev_demand', 'up'],
  ['employment', 'consumer_spending', 'up'],
  ['unemployment', 'consumer_spending', 'down'],
  ['consumer_spending', 'retail_sales', 'up'],
  ['consumer_spending', 'gdp_growth', 'up'],
  ['gdp_growth', 'corp_earnings', 'up'],
  ['recession_fear', 'corp_earnings', 'down'],

  // 가짜 — 테마 사이 (접었을 때 테마끼리 이어지는지 보려고)
  ['import_price', 'inflation', 'up'],
  ['us_rate', 'bond_yield', 'up'],
  ['exporter_earnings', 'semi_earnings', 'up'],
  ['semi_export', 'exporter_earnings', 'up'],
  ['oil_price', 'inflation', 'up'],
  ['dollar_index', 'oil_price', 'down'],
  ['interest_burden', 'consumer_spending', 'down'],
  ['inflation', 'consumer_spending', 'down'],
  ['recession_fear', 'bond_yield', 'down'],
  ['ai_investment', 'gdp_growth', 'up'],
  ['semi_earnings', 'volume_spike', 'up'],
]

const nodes: MapNode[] = NODE_ROWS.map(([id, name, theme, correct, total]) => ({
  id,
  name,
  theme,
  correct,
  total,
  learned: total > 0,
}))

const edges: MapEdge[] = EDGE_ROWS.map(([from, to, forceDir]) => ({ from, to, forceDir }))

/** 개념 48개 · 연결 57개 */
export const causalMapMock: CausalMap = { nodes, edges }
