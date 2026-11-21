import { useQuery } from '@tanstack/react-query'
import { apiClient, USE_MOCK } from '@/api/client'
import { calendarMock } from '@/api/mocks/calendar'
import { causalMapMock } from '@/api/mocks/causalMap'
import { reviewMock, summaryMock } from '@/api/mocks/review'
import { getUserId } from '@/lib/userId'
import type { CausalMap, Review, StudyCalendar, Summary } from '@/types/causalMap'

/**
 * 탭3 마이페이지 API (B, server mypage 패키지). VITE_USE_MOCK 이 'false' 가 아니면 목 데이터.
 * - 인과 지도: GET /api/mypage/map?userId=...
 * - 다시 보는 개념: GET /api/mypage/review?userId=...
 * - 홈 숫자: GET /api/mypage/summary?userId=...
 * - 학습 달력: GET /api/mypage/calendar?userId=...
 */
const fetchCausalMap = async (): Promise<CausalMap> => {
  if (USE_MOCK) return causalMapMock
  const { data } = await apiClient.get<CausalMap>('/api/mypage/map', {
    params: { userId: getUserId() },
  })
  return data
}

const fetchReview = async (): Promise<Review> => {
  if (USE_MOCK) return reviewMock
  const { data } = await apiClient.get<Review>('/api/mypage/review', {
    params: { userId: getUserId() },
  })
  return data
}

/**
 * 탭1에서 문제를 풀면 user_concepts 가 바로 바뀌므로, 마이페이지에 들어올 때마다 다시 읽는다
 * (앱 기본 staleTime 60초를 쓰면 방금 푼 결과가 1분 동안 안 보인다).
 */
const MYPAGE_STALE_TIME = 0

const fetchSummary = async (): Promise<Summary> => {
  if (USE_MOCK) return summaryMock
  const { data } = await apiClient.get<Summary>('/api/mypage/summary', {
    params: { userId: getUserId() },
  })
  return data
}

const fetchCalendar = async (): Promise<StudyCalendar> => {
  if (USE_MOCK) return calendarMock
  const { data } = await apiClient.get<StudyCalendar>('/api/mypage/calendar', {
    params: { userId: getUserId() },
  })
  return data
}

export const CALENDAR_KEY = ['mypage', 'calendar'] as const
export const CAUSAL_MAP_KEY = ['mypage', 'map'] as const
export const REVIEW_KEY = ['mypage', 'review'] as const
export const SUMMARY_KEY = ['mypage', 'summary'] as const

export const useCausalMap = () => {
  return useQuery({
    queryKey: CAUSAL_MAP_KEY,
    queryFn: fetchCausalMap,
    staleTime: MYPAGE_STALE_TIME,
  })
}

export const useReview = () => {
  return useQuery({ queryKey: REVIEW_KEY, queryFn: fetchReview, staleTime: MYPAGE_STALE_TIME })
}

export const useSummary = () => {
  return useQuery({ queryKey: SUMMARY_KEY, queryFn: fetchSummary, staleTime: MYPAGE_STALE_TIME })
}

export const useCalendar = () => {
  return useQuery({
    queryKey: CALENDAR_KEY,
    queryFn: fetchCalendar,
    staleTime: MYPAGE_STALE_TIME,
  })
}
