import { useQuery } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { apiClient, USE_MOCK } from '@/api/client'
import { etfDailyMock } from '@/api/mocks/etfDaily'
import { overlapListMock, stockDetailMock } from '@/api/mocks/overlap'
import { getUserId } from '@/lib/userId'
import type { EtfDaily } from '@/types/etf'
import type { OverlapList, StockDetail } from '@/types/overlap'

/**
 * 탭2 API: 겹침 목록·종목 상세(#97, docs/modules/overlap_api.md)와 ETF 어제 변화(docs/modules/etf_daily_api.md).
 * VITE_USE_MOCK 이 'false' 가 아니면 목 데이터.
 */

/** 최근 계산일의 겹침 결과에 없는 종목 (서버 404) */
export class StockNotFoundError extends Error {}

const fetchOverlaps = async (): Promise<OverlapList> => {
  if (USE_MOCK) return overlapListMock
  const { data } = await apiClient.get<OverlapList>('/api/overlaps')
  return data
}

/** 종목 상세: 카드 ① + 카드 ②③(#101) + "내 지도에 있어요". userId 로 배운 개념을 표시한다 */
const fetchStock = async (ticker: string): Promise<StockDetail> => {
  if (USE_MOCK) {
    const stock = stockDetailMock(ticker)
    if (!stock) throw new StockNotFoundError(ticker)
    return stock
  }
  try {
    const { data } = await apiClient.get<StockDetail>(`/api/stocks/${encodeURIComponent(ticker)}`, {
      params: { userId: getUserId() },
    })
    return data
  } catch (e) {
    if (isAxiosError(e) && e.response?.status === 404) throw new StockNotFoundError(ticker)
    throw e
  }
}

const fetchEtfDaily = async (): Promise<EtfDaily> => {
  if (USE_MOCK) return etfDailyMock
  const { data } = await apiClient.get<EtfDaily>('/api/etf/daily')
  return data
}

export const useOverlaps = () => {
  return useQuery({ queryKey: ['overlaps'], queryFn: fetchOverlaps })
}

export const useStockOverlap = (ticker: string) => {
  return useQuery({
    queryKey: ['stocks', ticker],
    queryFn: () => fetchStock(ticker),
    // 없는 종목은 다시 불러도 없다
    retry: (count, error) => !(error instanceof StockNotFoundError) && count < 1,
  })
}

export const useEtfDaily = () => {
  return useQuery({ queryKey: ['etf', 'daily'], queryFn: fetchEtfDaily })
}
