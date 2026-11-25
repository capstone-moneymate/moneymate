import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient, USE_MOCK } from '@/api/client'
import { mockTutorAnswer, mockTutorStart } from '@/api/mocks/tutor'
import { getUserId } from '@/lib/userId'
import type { AnswerMeta } from '@/types/card'
import type { TutorAnswer, TutorState } from '@/types/tutor'

/**
 * 개념 단계 튜터 API (server tutor 패키지 → 채점 서버 /tutor, docs/modules/tutor_server_api.md).
 * VITE_USE_MOCK 이 'false' 가 아니면 목 데이터.
 * - 시작: POST /api/tutor/start {userId, cardId} → 첫 퀴즈(또는 끝)까지의 이벤트
 * - 답:   POST /api/tutor/{sessionId}/answer {userId, answer, confidence, responseMs, answerChanges}
 *         → 채점(graded) + 다음 퀴즈(또는 끝)까지의 새 이벤트
 * 실패: 채점 서버가 꺼졌거나 시간 초과 503, 없는 카드·세션 404. 그러면 화면은 기존 개념 설명으로 넘어간다.
 */

/** 튜터가 한 요청에 모델을 여러 번 부르고 퀴즈도 만든다. Spring 이 채점 서버를 90초 기다리므로 그보다 길게 둔다 */
const TUTOR_TIMEOUT_MS = 100_000

const startTutor = async (cardId: string): Promise<TutorState> => {
  if (USE_MOCK) return mockTutorStart(cardId)
  const { data } = await apiClient.post<TutorState>(
    '/api/tutor/start',
    { userId: getUserId(), cardId: Number(cardId) },
    { timeout: TUTOR_TIMEOUT_MS },
  )
  return data
}

const answerTutor = async ({
  sessionId,
  answer,
  meta,
}: {
  sessionId: string
  answer: TutorAnswer
  meta: AnswerMeta
}): Promise<TutorState> => {
  if (USE_MOCK) return mockTutorAnswer(sessionId, answer)
  const { data } = await apiClient.post<TutorState>(
    `/api/tutor/${encodeURIComponent(sessionId)}/answer`,
    { userId: getUserId(), answer, ...meta },
    { timeout: TUTOR_TIMEOUT_MS },
  )
  return data
}

/**
 * 카드의 개념 단계 세션을 연다. 다시 부르면 세션을 또 만들고 모델 비용이 들어서
 * 저절로 다시 부르지 않고(retry·포커스 갱신 끔), 화면을 떠나면 버린다(gcTime 0).
 */
export const useTutorStart = (cardId: string) => {
  return useQuery({
    queryKey: ['tutor', 'start', cardId],
    queryFn: () => startTutor(cardId),
    staleTime: Infinity,
    gcTime: 0,
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export const useTutorAnswer = () => {
  return useMutation({ mutationFn: answerTutor })
}
