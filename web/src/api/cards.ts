import { useMutation, useQuery } from '@tanstack/react-query'
import { answerMocks, cardDetailMocks } from '@/api/mocks/cardDetail'
import type { AnswerInput, AnswerResult, CardDetail, RubricGrade } from '@/types/card'

/** 카드 한 건(카드뉴스 + 단계). 서버가 생기면 apiClient.get(`/api/cards/${cardId}`)로 바꾼다. */
const fetchCard = async (cardId: string): Promise<CardDetail> => {
  const card = cardDetailMocks[cardId]
  if (!card) throw new Error(`카드를 찾을 수 없어요: ${cardId}`)
  return card
}

export const useCard = (cardId: string) => {
  return useQuery({ queryKey: ['cards', cardId], queryFn: () => fetchCard(cardId) })
}

/**
 * 답안 제출. 서버가 생기면
 * - 퀴즈·인과 순서·차트: apiClient.post('/api/answers', …) (C, 코드 채점)
 * - 판단해보기·주관식: apiClient.post('/api/judgement', …) (A, 루브릭 채점)
 * 으로 바꾼다. 지금은 목 정답과 목 채점으로 돌려준다.
 */
const submitAnswer = async ({
  stepId,
  answer,
}: {
  stepId: string
  answer: AnswerInput
}): Promise<AnswerResult> => {
  if (answer.kind === 'judgement' || answer.kind === 'open_ended') {
    return { stepId, isCorrect: null, grade: mockRubricGrade(answer.reason) }
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

/**
 * 목 루브릭 채점 (화면 확인용). A의 키워드 규칙 채점(rule_judge.py)이 생기기 전까지만 쓴다.
 * 근거에 숫자가 있으면 증거, 연결어 수만큼 추론, 반박어가 있으면 반박 점수를 준다. 7점 → 100점 환산.
 */
const mockRubricGrade = (reason: string): RubricGrade => {
  const evidence = Math.min(2, (reason.match(/\d/g) ? 1 : 0) + (reason.length >= 60 ? 1 : 0))
  const links = reason.match(/때문|그래서|따라서|이어|그러면|늘면|오르면|줄면/g)?.length ?? 0
  const reasoning = Math.min(3, links)
  const rebuttal = Math.min(2, reason.match(/다만|하지만|반대로|위험|그런데/g)?.length ?? 0)
  const score = Math.round(((evidence + reasoning + rebuttal) / 7) * 100)
  return {
    score,
    rubric: { evidence, reasoning, rebuttal },
    feedback: {
      good:
        reasoning > 0
          ? '사건에서 판단까지 이어지는 연결을 직접 써 줬어요.'
          : '자신의 판단을 분명하게 골랐어요.',
      consider:
        rebuttal > 0
          ? '근거에 자료 속 숫자를 하나 더 붙이면 더 단단해져요.'
          : '반대로 움직일 수 있는 다른 힘이나 위험도 한 가지 적어 보세요.',
      skeleton: [],
    },
  }
}
