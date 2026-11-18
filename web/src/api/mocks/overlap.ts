import type { OverlapList, StockDetail, StockOverlap } from '@/types/overlap'

/**
 * 탭2 겹침 목 데이터. #97 통합 테스트 fixture(server/src/test/resources/fixtures/overlap.sql)의 응답과 같은 값이다.
 * 수치는 예시이고 실제 공시가 아니다.
 */
const nvda: StockOverlap = {
  calcDate: '2026-11-14',
  ticker: 'NVDA',
  issuerName: 'NVIDIA CORPORATION',
  etfStockName: 'NVIDIA CORP',
  filers: [
    {
      filerKey: 'druckenmiller',
      filerName: 'Duquesne Family Office LLC',
      changeType: 'increase',
      chgPct: 0.1,
      periodEnd: '2026-06-30',
      filedAt: '2026-08-14',
    },
    {
      filerKey: 'thiel',
      filerName: 'Thiel Macro LLC',
      changeType: 'new',
      chgPct: null,
      periodEnd: '2026-06-30',
      filedAt: '2026-08-13',
    },
  ],
  etfs: [
    { etfCode: '0015B0', snapshotDate: '2026-11-13', trendChgPct: 0.05, dayChgPct: 0.01 },
    { etfCode: '426030', snapshotDate: '2026-11-13', trendChgPct: -0.16318, dayChgPct: -0.02 },
  ],
  pairs: [
    { filerKey: 'druckenmiller', etfCode: '0015B0', direction: 'same' },
    { filerKey: 'druckenmiller', etfCode: '426030', direction: 'diff' },
    { filerKey: 'thiel', etfCode: '0015B0', direction: 'same' },
    { filerKey: 'thiel', etfCode: '426030', direction: 'diff' },
  ],
}

const googl: StockOverlap = {
  calcDate: '2026-11-14',
  ticker: 'GOOGL',
  issuerName: 'ALPHABET INC',
  etfStockName: 'ALPHABET INC-CL A',
  filers: [
    {
      filerKey: 'ackman',
      filerName: 'Pershing Square Inc.',
      changeType: 'decrease',
      chgPct: -0.25,
      periodEnd: '2026-06-30',
      filedAt: '2026-08-14',
    },
  ],
  etfs: [{ etfCode: '0015B0', snapshotDate: '2026-11-13', trendChgPct: 0.1, dayChgPct: 0 }],
  pairs: [{ filerKey: 'ackman', etfCode: '0015B0', direction: 'diff' }],
}

export const overlapListMock: OverlapList = { calcDate: '2026-11-14', stocks: [googl, nvda] }

/**
 * 종목 상세 목 (#101). NVDA 는 카드 ②③ 과 "내 지도에 있어요"가 있는 경우, GOOGL 은 이유가 아직 없는 경우.
 * 이유·근거·숫자는 화면 확인용 예시이고 실제 자료가 아니다 (링크는 example.com).
 */
const nvdaDetail: StockDetail = {
  ...nvda,
  reasons: {
    bigPeriodEnd: '2026-06-30',
    direction: 'diff',
    change: 'up',
    headline: '왜 방향이 다를까요?',
    reasons: [
      {
        title: 'AI 데이터센터 투자 확대',
        body: '빅테크가 데이터센터 투자를 늘린다고 밝히면서 AI 반도체 수요가 커질 것으로 봤을 수 있어요.',
        path: [
          { id: 'ai_investment', name: 'AI 데이터센터 투자', learned: false },
          { id: 'gpu_demand', name: 'AI 반도체 수요', learned: true },
          { id: 'semi_earnings', name: '반도체 기업 실적', learned: false },
        ],
        direction: 'up',
        inMyMap: true,
        evidence: [
          {
            no: 4,
            publishedDate: '2026-06-12',
            title: '(예시) 데이터센터 설비투자 확대 발표',
            issuerName: '예시 기관',
            url: 'https://example.com/a',
          },
          {
            no: 11,
            publishedDate: '2026-05-28',
            title: '(예시) 1분기 실적 발표',
            issuerName: '예시 기업',
            url: 'https://example.com/b',
          },
        ],
      },
      {
        title: '메모리 가격 부담',
        body: 'ETF 매니저는 분기 말 이후 부품 가격 부담을 더 크게 봤을 수 있어요.',
        path: [
          { id: 'memory_price', name: '범용 메모리(D램) 가격', learned: false },
          { id: 'semi_earnings', name: '반도체 기업 실적', learned: false },
        ],
        direction: 'down',
        inMyMap: false,
        evidence: [
          {
            no: 11,
            publishedDate: '2026-05-28',
            title: '(예시) 1분기 실적 발표',
            issuerName: '예시 기업',
            url: 'https://example.com/b',
          },
        ],
      },
    ],
    now: {
      baseDate: '2026-06-30',
      price: {
        fromDate: '2026-06-30',
        fromClose: 100,
        toDate: '2026-11-14',
        toClose: 112.5,
        returnPct: 12.5,
      },
      laterSources: [
        {
          publishedDate: '2026-11-12',
          title: '(예시) 3분기 실적 발표',
          url: 'https://example.com/c',
          numbers: { '매출액 전년동기대비(%)': 62, '영업이익 전년동기대비 방향': '증가' },
        },
      ],
      linked: [
        { conceptId: 'gpu_demand', name: 'AI 반도체 수요', reasonTitle: 'AI 데이터센터 투자 확대' },
      ],
      text: '기준일 뒤 주가는 12.5% 올랐어요. 그 사이 3분기 실적 발표가 있었어요.',
    },
  },
  reasonsRejected: false,
  myConcepts: [{ id: 'gpu_demand', name: 'AI 반도체 수요', theme: 'AI·반도체' }],
}

/** GOOGL 은 서버 fixture 처럼 이유가 전부 버려진(rejected) 종목 */
const googlDetail: StockDetail = { ...googl, reasons: null, reasonsRejected: true, myConcepts: [] }

export const stockDetailMock = (ticker: string): StockDetail | undefined =>
  [nvdaDetail, googlDetail].find((s) => s.ticker === ticker.trim().toUpperCase())
