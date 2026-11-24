import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient, USE_MOCK } from '@/api/client'
import {
  calibrationMock,
  mockReviewAnswer,
  mockReviewQuiz,
  reviewQueueMock,
} from '@/api/mocks/learner'
import { getUserId } from '@/lib/userId'
import type { AnswerMeta } from '@/types/card'
import type { Calibration, ReviewQueue, ReviewQuiz, ReviewResult } from '@/types/learner'

/**
 * 학습자 상태 조회 API (server learning 패키지 → 채점 서버 /learner, docs/modules/learner_api.md).
 * VITE_USE_MOCK 이 'false' 가 아니면 목 데이터.
 * - 오늘의 복습: GET /api/learner/reviews?userId=...
 * - 확신 점검:   GET /api/learner/calibration?userId=...
 * - 복습 문제:   POST /api/learner/review/quiz {userId, nodeId} (정답 없이 문제만 온다)
 * - 복습 채점:   POST /api/learner/review/answer {userId, quizId, answer, confidence, responseMs, answerChanges}
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

/**
 * 문제를 만드는 동안(서버가 LLM 을 부른다) 기다리는 시간. Spring 이 채점 서버를 최대 32초 기다리므로 그보다 길게 둔다.
 */
const REVIEW_QUIZ_TIMEOUT_MS = 40_000

const fetchReviewQuiz = async (nodeId: number): Promise<ReviewQuiz> => {
  if (USE_MOCK) return mockReviewQuiz(nodeId)
  const { data } = await apiClient.post<ReviewQuiz>(
    '/api/learner/review/quiz',
    { userId: getUserId(), nodeId },
    { timeout: REVIEW_QUIZ_TIMEOUT_MS },
  )
  return data
}

const submitReviewAnswer = async ({
  quizId,
  answer,
  meta,
}: {
  quizId: number
  answer: number
  meta: AnswerMeta
}): Promise<ReviewResult> => {
  if (USE_MOCK) return mockReviewAnswer(quizId, answer)
  const { data } = await apiClient.post<ReviewResult>('/api/learner/review/answer', {
    userId: getUserId(),
    quizId,
    answer,
    ...meta,
  })
  return data
}

/**
 * 복습할 개념의 문제 하나. 안 푼 문제가 있으면 서버가 같은 문제를 다시 준다.
 * 실패해도 저절로 다시 부르지 않는다 (다시 부르면 문제를 또 만든다). 화면의 "다시 시도"로만 부른다.
 */
export const useReviewQuiz = (nodeId: number) => {
  return useQuery({
    queryKey: ['learner', 'review-quiz', nodeId],
    queryFn: () => fetchReviewQuiz(nodeId),
    staleTime: Infinity,
    gcTime: 0,
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export const useSubmitReviewAnswer = () => {
  return useMutation({ mutationFn: submitReviewAnswer })
}
