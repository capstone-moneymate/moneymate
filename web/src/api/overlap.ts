import { useQuery } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { apiClient, USE_MOCK } from '@/api/client'
import { etfDailyMock } from '@/api/mocks/etfDaily'
import { overlapListMock } from '@/api/mocks/overlap'
import type { EtfDaily } from '@/types/etf'
import type { OverlapList, StockOverlap } from '@/types/overlap'

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

const fetchStock = async (ticker: string): Promise<StockOverlap> => {
  if (USE_MOCK) {
    const stock = overlapListMock.stocks.find((s) => s.ticker === ticker.toUpperCase())
    if (!stock) throw new StockNotFoundError(ticker)
    return stock
  }
  try {
    const { data } = await apiClient.get<StockOverlap>(`/api/stocks/${encodeURIComponent(ticker)}`)
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
