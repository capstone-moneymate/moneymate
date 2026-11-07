import { useQuery } from '@tanstack/react-query'
import { apiClient, USE_MOCK } from '@/api/client'
import { newsHomeMock } from '@/api/mocks/newsHome'
import { getUserId } from '@/lib/userId'
import type { NewsHome } from '@/types/news'

/**
 * 탭1 뉴스 홈: C의 GET /api/news/home (docs/modules/news_api.md).
 * userId 를 같이 보내 학습을 끝낸 카드(completedCardIds)를 받는다. VITE_USE_MOCK 이 'false' 가 아니면 목 데이터.
 */
const fetchNewsHome = async (): Promise<NewsHome> => {
  if (USE_MOCK) return newsHomeMock
  const { data } = await apiClient.get<NewsHome>('/api/news/home', {
    params: { userId: getUserId() },
  })
  return data
}

export const NEWS_HOME_KEY = ['news', 'home'] as const

export const useNewsHome = () => {
  return useQuery({ queryKey: NEWS_HOME_KEY, queryFn: fetchNewsHome })
}
