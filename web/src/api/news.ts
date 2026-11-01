import { useQuery } from '@tanstack/react-query'
import { newsHomeMock } from '@/api/mocks/newsHome'
import type { NewsHome } from '@/types/news'

/** 탭1 뉴스 홈. 지금은 목 데이터를 돌려주고, 서버 news.ts가 생기면 apiClient.get('/api/news/home')으로 바꾼다. */
const fetchNewsHome = async (): Promise<NewsHome> => {
  return newsHomeMock
}

export const useNewsHome = () => {
  return useQuery({ queryKey: ['news', 'home'], queryFn: fetchNewsHome })
}
