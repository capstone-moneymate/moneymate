import type { ChartData } from '@/types/chart'

/**
 * 화면 확인용 가상 데이터 (실제 시세 아님). 단계 id별로 둔다.
 * cardDetail.ts 의 목 정답과 맞춘다: rh-4 발표 날 거래량이 평소보다 많음, kp-3 셋째 날 거래량이 가장 많음.
 */
export const chartMocks: Record<string, ChartData> = {
  'rh-4': {
    highlight: { date: '2026-10-22', label: '발표 날' },
    points: [
      { date: '2026-09-24', close: 3410, volume: 412000 },
      { date: '2026-09-25', close: 3398, volume: 398000 },
      { date: '2026-09-28', close: 3425, volume: 405000 },
      { date: '2026-09-29', close: 3431, volume: 421000 },
      { date: '2026-09-30', close: 3418, volume: 389000 },
      { date: '2026-10-01', close: 3442, volume: 433000 },
      { date: '2026-10-02', close: 3456, volume: 415000 },
      { date: '2026-10-06', close: 3449, volume: 402000 },
      { date: '2026-10-07', close: 3463, volume: 418000 },
      { date: '2026-10-08', close: 3471, volume: 427000 },
      { date: '2026-10-12', close: 3458, volume: 396000 },
      { date: '2026-10-13', close: 3466, volume: 408000 },
      { date: '2026-10-14', close: 3480, volume: 431000 },
      { date: '2026-10-15', close: 3475, volume: 411000 },
      { date: '2026-10-16', close: 3488, volume: 424000 },
      { date: '2026-10-19', close: 3494, volume: 417000 },
      { date: '2026-10-20', close: 3486, volume: 403000 },
      { date: '2026-10-21', close: 3497, volume: 429000 },
      { date: '2026-10-22', close: 3522, volume: 688000 },
    ],
  },
  'kp-3': {
    points: [
      { date: '2026-10-28', close: 3510, volume: 420000 },
      { date: '2026-10-29', close: 3534, volume: 465000 },
      { date: '2026-10-30', close: 3571, volume: 612000 },
    ],
  },
}
