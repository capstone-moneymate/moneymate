import { answerMocks } from '@/api/mocks/cardDetail'
import type { AnswerResult, PastAnswer, PastInput } from '@/types/card'

/**
 * "풀었던 내용 보기" 목 데이터 (가짜 답). 날짜와 상관없이 카드마다 같은 답을 돌려준다.
 * 코드 채점 단계는 목 정답(answerMocks)으로 맞음·틀림을 정한다.
 */
const coded = (stepId: string, input: PastInput): PastAnswer => {
  const key = answerMocks[stepId]
  const isCorrect =
    input.kind === 'causal_order'
      ? JSON.stringify(input.order) === JSON.stringify(key.correct)
      : input.kind !== 'judgement' && input.optionIndex === key.correct
  const result: AnswerResult = {
    stepId,
    isCorrect,
    explanation: key.explanation,
    correct: key.correct,
  }
  return { stepId, input, result }
}

const judged = (stepId: string, choice: string, reason: string, score: number): PastAnswer => ({
  stepId,
  input: { kind: 'judgement', choice, reason },
  result: {
    stepId,
    isCorrect: null,
    grade: {
      score,
      correct: score >= 60,
      rubric: { evidence: 2, reasoning: 2, rebuttal: 1 },
      reasons: {},
      grader: 'claude',
      reused: false,
      message: null,
      feedback: {
        good: '뉴스 속 사실(기준금리 동결)을 근거로 들었어요.',
        thinkMore: '반대로 움직일 수 있는 이유도 한 가지 적어 보면 더 단단해져요.',
        chain: [
          { name: '기준금리 동결', used: true },
          { name: '시장금리', used: false },
        ],
        chainComment: '동결이 시장금리에 어떤 영향을 주는지까지 이어 보세요.',
      },
    },
  },
})

export const pastAnswerMocks: Record<string, PastAnswer[]> = {
  'mock-rate-hold': [
    coded('rh-2', { kind: 'quiz', optionIndex: 2 }),
    coded('rh-3', { kind: 'causal_order', order: ['bond_yield', 'rate_hold', 'growth_valuation'] }),
    coded('rh-4', { kind: 'chart', optionIndex: 0 }),
    judged(
      'rh-5',
      '은행주 흐름을 더 지켜본다',
      '금리가 그대로 유지되면 예대마진이 유지돼서 은행주에 유리할 것 같아요.',
      67,
    ),
  ],
  'mock-hbm4': [
    judged(
      'hb-2',
      'AI 칩 수요가 이어진다고 봤을 것 같다',
      '공급계약 규모가 커서 실적에 반영될 것 같아요.',
      56,
    ),
  ],
  'mock-kospi-3up': [
    coded('kp-2', { kind: 'quiz', optionIndex: 0 }),
    coded('kp-3', { kind: 'chart', optionIndex: 2 }),
  ],
}
