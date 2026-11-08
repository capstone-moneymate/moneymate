import { useMutation, useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { apiClient, DailyLimitError, USE_MOCK } from '@/api/client'
import { answerMocks, cardDetailMocks } from '@/api/mocks/cardDetail'
import { mockJudgement } from '@/api/mocks/judgement'
import { getUserId } from '@/lib/userId'
import type { AnswerInput, AnswerResult, CardDetail, JudgementGrade } from '@/types/card'

/** 카드 한 건(카드뉴스 + 단계). 서버가 생기면 apiClient.get(`/api/cards/${cardId}`)로 바꾼다. */
const fetchCard = async (cardId: string): Promise<CardDetail> => {
  const card = cardDetailMocks[cardId]
  if (!card) throw new Error(`카드를 찾을 수 없어요: ${cardId}`)
  return card
}

export const useCard = (cardId: string) => {
  return useQuery({ queryKey: ['cards', cardId], queryFn: () => fetchCard(cardId) })
}

type JudgementAnswer = Extract<AnswerInput, { kind: 'judgement' }>

/**
 * 판단 채점 요청만 기다리는 시간(ms). Spring 이 채점 서버를 최대 33초(연결 3초 + 응답
 * JUDGE_API_TIMEOUT_SECONDS 기본 30초) 기다린 뒤 결과나 고정 문구를 주므로, 그보다 길게 둔다.
 * 기본 10초면 Claude 채점이 길 때 화면만 먼저 실패해 같은 답을 다시 내게 된다 (#72 리뷰).
 */
const JUDGEMENT_TIMEOUT_MS = 40_000

/** 판단해보기 근거 채점: A의 POST /api/judgement (docs/modules/judgement_api.md) */
const submitJudgement = async (
  stepId: string,
  answer: JudgementAnswer,
): Promise<JudgementGrade> => {
  if (USE_MOCK) return mockJudgement(stepId, answer.reason)
  try {
    const { data } = await apiClient.post<JudgementGrade>(
      '/api/judgement',
      {
        userId: getUserId(),
        stepId: Number(stepId),
        choice: answer.choice, // 채점하지 않고 저장만 한다
        answer: answer.reason,
      },
      { timeout: JUDGEMENT_TIMEOUT_MS },
    )
    return data
  } catch (e) {
    if (axios.isAxiosError<{ message?: string }>(e) && e.response?.status === 429) {
      throw new DailyLimitError(e.response.data?.message ?? '오늘 판단 채점 횟수를 다 썼어요.')
    }
    throw e
  }
}

/**
 * 답안 제출.
 * - 판단해보기: A의 /api/judgement (루브릭 채점). VITE_USE_MOCK 이 'false' 가 아니면 목 채점
 * - 퀴즈·인과 순서·차트: 서버가 생기면 apiClient.post('/api/answers', …) (C, 코드 채점). 지금은 목 정답
 */
const submitAnswer = async ({
  stepId,
  answer,
}: {
  stepId: string
  answer: AnswerInput
}): Promise<AnswerResult> => {
  if (answer.kind === 'judgement') {
    return { stepId, isCorrect: null, grade: await submitJudgement(stepId, answer) }
  }
  const key = answerMocks[stepId]
  if (!key) throw new Error(`정답이 없는 단계예요: ${stepId}`)
  const isCorrect =
    answer.kind === 'causal_order'
      ? JSON.stringify(answer.order) === JSON.stringify(key.correct)
      : answer.optionIndex === key.correct
  return { stepId, isCorrect, explanation: key.explanation, correct: key.correct }
}

export const useSubmitAnswer = () => {
  return useMutation({ mutationFn: submitAnswer })
}
