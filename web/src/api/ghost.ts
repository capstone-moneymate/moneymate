import { useQuery } from '@tanstack/react-query'
import { apiClient, USE_MOCK } from '@/api/client'
import { ghostMocks } from '@/api/mocks/ghost'
import { getUserId } from '@/lib/userId'
import type { GhostReport } from '@/types/ghost'

/**
 * 고스트 비교 (추가 구현 2-6): GET /api/answers/ghost?userId=...&cardId=... (docs/modules/ghost.md).
 * 이 카드를 풀어 본 적이 없으면 lastComplete·comparison 이 모두 null 이다. VITE_USE_MOCK 이 'false' 가 아니면 목 데이터.
 */
const fetchGhost = async (cardId: string): Promise<GhostReport> => {
  if (USE_MOCK) return ghostMocks[cardId] ?? { lastComplete: null, comparison: null }
  const { data } = await apiClient.get<GhostReport>('/api/answers/ghost', {
    params: { userId: getUserId(), cardId },
  })
  return data
}

/**
 * when: 'learn' 은 풀기 시작할 때 한 번(지난 기록), 'result' 는 다 푼 뒤(이번 기록이 들어간 비교).
 * 답을 내면 값이 바뀌므로 화면에 들어올 때마다 새로 읽고(gcTime 0), 푸는 도중에는 다시 읽지 않는다.
 */
export const useGhost = (cardId: string, when: 'learn' | 'result', enabled: boolean) => {
  return useQuery({
    queryKey: ['answers', 'ghost', cardId, when],
    queryFn: () => fetchGhost(cardId),
    enabled,
    staleTime: Infinity,
    gcTime: 0,
    refetchOnWindowFocus: false,
  })
}
