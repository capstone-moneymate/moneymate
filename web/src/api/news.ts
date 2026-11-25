import { useQuery } from '@tanstack/react-query'
import { apiClient, USE_MOCK } from '@/api/client'
import { newsHomeMock, pastNewsMock } from '@/api/mocks/newsHome'
import { getUserId } from '@/lib/userId'
import type { NewsHome, PastNews } from '@/types/news'

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

/**
 * 지난 뉴스 목록: GET /api/news/past (홈에 보이는 날짜보다 앞선 카드, 최근 날짜부터).
 * 홈의 "지난 뉴스"와 검색이 쓴다. 못 불러와도 홈의 나머지는 그대로 보인다.
 */
const fetchPastNews = async (): Promise<PastNews> => {
  if (USE_MOCK) return pastNewsMock
  const { data } = await apiClient.get<PastNews>('/api/news/past', {
    params: { userId: getUserId() },
  })
  return data
}

export const usePastNews = () => {
  return useQuery({ queryKey: ['news', 'past'], queryFn: fetchPastNews })
}
