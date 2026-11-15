import { useQuery } from '@tanstack/react-query'
import { chartMocks } from '@/api/mocks/chart'
import type { ChartData } from '@/types/chart'

/**
 * 차트 읽기 데이터. 지금은 단계 id로 목 데이터를 찾는다.
 * API 가 생기면 종목·표시 기간으로 바꾼다 (기간을 steps.content 에 넣을지는 C와 정한다).
 */
const fetchChart = async (stepId: string): Promise<ChartData> => {
  const chart = chartMocks[stepId]
  if (!chart) throw new Error(`차트 데이터가 없어요: ${stepId}`)
  return chart
}

export const useChart = (stepId: string) => {
  return useQuery({ queryKey: ['charts', stepId], queryFn: () => fetchChart(stepId) })
}
