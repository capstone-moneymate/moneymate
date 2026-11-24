import { useQuery } from '@tanstack/react-query'
import { apiClient, USE_MOCK } from '@/api/client'
import { calibrationMock, reviewQueueMock } from '@/api/mocks/learner'
import { getUserId } from '@/lib/userId'
import type { Calibration, ReviewQueue } from '@/types/learner'

/**
 * 학습자 상태 조회 API (server learning 패키지 → 채점 서버 /learner, docs/modules/learner_api.md).
 * VITE_USE_MOCK 이 'false' 가 아니면 목 데이터.
 * - 오늘의 복습: GET /api/learner/reviews?userId=...
 * - 확신 점검:   GET /api/learner/calibration?userId=...
 * 채점 서버가 꺼져 있으면 503 이 온다 (화면은 "불러오지 못했어요").
 */
const fetchReviews = async (): Promise<ReviewQueue> => {
  if (USE_MOCK) return reviewQueueMock
  const { data } = await apiClient.get<ReviewQueue>('/api/learner/reviews', {
    params: { userId: getUserId() },
  })
  return data
}

const fetchCalibration = async (): Promise<Calibration> => {
  if (USE_MOCK) return calibrationMock
  const { data } = await apiClient.get<Calibration>('/api/learner/calibration', {
    params: { userId: getUserId() },
  })
  return data
}

export const LEARNER_REVIEWS_KEY = ['learner', 'reviews'] as const
export const LEARNER_CALIBRATION_KEY = ['learner', 'calibration'] as const

/** 문제를 풀면 바로 바뀌므로 들어올 때마다 다시 읽는다 (마이페이지의 다른 조회와 같다) */
export const useReviews = () => {
  return useQuery({ queryKey: LEARNER_REVIEWS_KEY, queryFn: fetchReviews, staleTime: 0 })
}

export const useCalibration = () => {
  return useQuery({ queryKey: LEARNER_CALIBRATION_KEY, queryFn: fetchCalibration, staleTime: 0 })
}
