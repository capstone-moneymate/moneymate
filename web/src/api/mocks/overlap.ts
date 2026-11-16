import type { OverlapList, StockOverlap } from '@/types/overlap'

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
