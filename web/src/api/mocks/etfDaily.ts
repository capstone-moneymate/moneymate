import type { EtfDaily } from '@/types/etf'

/**
 * 탭2 ETF 어제 변화 목 데이터. ETF API 통합 테스트 fixture(server/src/test/resources/fixtures/etf_daily.sql)의
 * 응답과 같은 값이다. 수치는 예시다.
 */
export const etfDailyMock: EtfDaily = {
  threshold: 0.05,
  etfs: [
    { etfCode: '0015B0', snapshotDate: '2026-11-13' },
    { etfCode: '426030', snapshotDate: '2026-11-13' },
  ],
  together: [
    {
      ticker: 'NVDA',
      rawCode: '7066G1',
      stockName: 'NVIDIA CORP',
      moves: [
        {
          etfCode: '0015B0',
          ticker: 'NVDA',
          rawCode: '7066G1',
          stockName: 'NVIDIA CORP',
          dayChgPct: 0.08,
        },
        {
          etfCode: '426030',
          ticker: null,
          rawCode: '7066G1',
          stockName: 'NVIDIA CORP',
          dayChgPct: 0.06,
        },
      ],
    },
  ],
  topIncrease: [
    {
      etfCode: '0015B0',
      ticker: 'AMZN',
      rawCode: '023135',
      stockName: 'AMAZON.COM INC',
      dayChgPct: 0.2,
    },
    {
      etfCode: '0015B0',
      ticker: 'NVDA',
      rawCode: '7066G1',
      stockName: 'NVIDIA CORP',
      dayChgPct: 0.08,
    },
    {
      etfCode: '426030',
      ticker: null,
      rawCode: '7066G1',
      stockName: 'NVIDIA CORP',
      dayChgPct: 0.06,
    },
  ],
  topDecrease: [
    {
      etfCode: '426030',
      ticker: 'MSFT',
      rawCode: '594918',
      stockName: 'MICROSOFT CORP',
      dayChgPct: -0.3,
    },
    {
      etfCode: '0015B0',
      ticker: 'AAPL',
      rawCode: '037833',
      stockName: 'APPLE INC',
      dayChgPct: -0.1,
    },
    {
      etfCode: '426030',
      ticker: 'META',
      rawCode: '30303M',
      stockName: 'META PLATFORMS INC',
      dayChgPct: -0.06,
    },
  ],
}
