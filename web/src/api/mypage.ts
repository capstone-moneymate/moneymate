import { useQuery } from '@tanstack/react-query'
import { apiClient, USE_MOCK } from '@/api/client'
import { causalMapMock } from '@/api/mocks/causalMap'
import { getUserId } from '@/lib/userId'
import type { CausalMap } from '@/types/causalMap'

/**
 * 탭3 인과 지도: B의 GET /api/mypage/map?userId=... (잠정 모양, types/causalMap.ts).
 * VITE_USE_MOCK 이 'false' 가 아니면 목 데이터. 실제 API로 바꿀 때 이 함수만 고친다.
 */
const fetchCausalMap = async (): Promise<CausalMap> => {
  if (USE_MOCK) return causalMapMock
  const { data } = await apiClient.get<CausalMap>('/api/mypage/map', {
    params: { userId: getUserId() },
  })
  return data
}

export const CAUSAL_MAP_KEY = ['mypage', 'map'] as const

export const useCausalMap = () => {
  return useQuery({ queryKey: CAUSAL_MAP_KEY, queryFn: fetchCausalMap })
}
