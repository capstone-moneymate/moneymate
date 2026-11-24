import type {
  Calibration,
  CalibrationSummary,
  ReviewQueue,
  ReviewQuiz,
  ReviewResult,
} from '@/types/learner'

/** 오늘의 복습 목 데이터 (가짜 값). 순서는 서버와 같다: 확실해요인데 틀린 개념 먼저, 나머지는 기억 확률 낮은 순 */
export const reviewQueueMock: ReviewQueue = {
  limit: 5,
  doneToday: 0,
  dueTotal: 7,
  items: [
    {
      nodeId: 4,
      concept: '성장주 가치평가',
      pKnow: 0.15,
      retrievability: 0.62,
      reason: 'sure_wrong',
      dueAt: new Date().toISOString(),
    },
    {
      nodeId: 2,
      concept: '예대금리차',
      pKnow: 0.34,
      retrievability: 0.71,
      reason: 'due',
      dueAt: new Date().toISOString(),
    },
    {
      nodeId: 1,
      concept: '기준금리 동결',
      pKnow: 0.65,
      retrievability: 0.84,
      reason: 'due',
      dueAt: new Date().toISOString(),
    },
    {
      nodeId: 7,
      concept: '시장금리',
      pKnow: 0.65,
      retrievability: 0.88,
      reason: 'due',
      dueAt: new Date().toISOString(),
    },
    {
      nodeId: 9,
      concept: '은행 실적',
      pKnow: 0.88,
      retrievability: 0.9,
      reason: 'due',
      dueAt: new Date().toISOString(),
    },
  ],
}

/** 2 × 2 개수로 지표를 만든다 (서버 learner/calibration.py 의 summarize 와 같은 식. 목 데이터 전용) */
const summarize = (
  sureRight: number,
  sureWrong: number,
  unsureRight: number,
  unsureWrong: number,
): CalibrationSummary => {
  const ratio = (a: number, b: number) => (b === 0 ? null : a / b)
  const total = sureRight + sureWrong + unsureRight + unsureWrong
  const sureAccuracy = ratio(sureRight, sureRight + sureWrong)
  const unsureAccuracy = ratio(unsureRight, unsureRight + unsureWrong)
  const specificity = ratio(unsureWrong, sureWrong + unsureWrong)
  return {
    total,
    enough: total >= 20,
    sureRight,
    sureWrong,
    unsureRight,
    unsureWrong,
    sensitivity: ratio(sureRight, sureRight + unsureRight),
    specificity,
    illusion: specificity === null ? null : 1 - specificity,
    sureAccuracy,
    unsureAccuracy,
    gap: sureAccuracy === null || unsureAccuracy === null ? null : sureAccuracy - unsureAccuracy,
    gamma: ratio(
      sureRight * unsureWrong - sureWrong * unsureRight,
      sureRight * unsureWrong + sureWrong * unsureRight,
    ),
    bias: ratio(sureWrong - unsureRight, total),
  }
}

/** 확신 점검 목 데이터 (가짜 값). 이전에는 확실해요인데 틀린 답이 많았다가 최근에 줄어든 사람 */
export const calibrationMock: Calibration = {
  all: summarize(27, 11, 8, 14),
  recent: summarize(16, 3, 5, 8),
  earlier: summarize(11, 8, 3, 6),
  recentDays: 30,
  sureWrongConcepts: ['성장주 가치평가', '할인율'],
}

/** 복습 문제 목 데이터 (가짜 문제). 오늘의 복습 목의 개념(nodeId)마다 하나씩. key 는 목 채점용 정답 */
type QuizMock = Pick<ReviewQuiz, 'kind' | 'content'> & { key: number; explanation: string }

const QUIZ_MOCKS: Record<number, QuizMock> = {
  // 성장주 가치평가
  4: {
    kind: '용어 뜻',
    content: {
      question: '성장주 가치평가에서 금리가 중요한 이유로 맞는 것은?',
      options: [
        '먼 미래의 이익을 오늘 가치로 바꿀 때 금리만큼 깎여서',
        '금리가 오르면 회사가 가진 주식 수가 늘어서',
        '금리가 곧 회사의 매출이라서',
      ],
    },
    key: 0,
    explanation:
      '성장주는 먼 미래 이익의 비중이 커서, 금리가 높으면 오늘 가치로 바꿀 때 더 많이 깎여요.',
  },
  // 예대금리차
  2: {
    kind: '틀린 설명',
    content: {
      question: '예대금리차에 대한 설명 중 틀린 것은?',
      options: [
        '대출 금리에서 예금 금리를 뺀 값이에요',
        '차이가 벌어지면 은행의 이자 이익이 늘기 쉬워요',
        '주식을 사고팔 때 내는 수수료예요',
      ],
    },
    key: 2,
    explanation: '예대금리차는 수수료가 아니라 대출 금리와 예금 금리의 차이예요.',
  },
  // 기준금리 동결
  1: {
    kind: 'O/X',
    content: { statement: '기준금리 동결은 금리를 올린다는 뜻이다.', options: ['O', 'X'] },
    key: 1,
    explanation: '동결은 올리지도 내리지도 않고 그대로 둔다는 뜻이에요.',
  },
  // 시장금리
  7: {
    kind: '용어 뜻',
    content: {
      question: '시장금리의 뜻으로 맞는 것은?',
      options: [
        '한국은행이 회의에서 정하는 정책 금리',
        '채권 시장에서 사고파는 사람들 사이에 정해지는 금리',
        '은행이 정한 예금 이자의 상한',
      ],
    },
    key: 1,
    explanation:
      '시장금리는 채권 같은 시장에서 수요와 공급으로 정해져요. 기준금리의 영향을 받지만 같은 값은 아니에요.',
  },
  // 은행 실적
  9: {
    kind: 'O/X',
    content: {
      statement: '은행의 이자 이익은 대출 이자에서 예금 이자를 뺀 것이다.',
      options: ['O', 'X'],
    },
    key: 0,
    explanation: '빌려주고 받은 이자에서 예금에 준 이자를 뺀 것이 이자 이익이에요.',
  },
}

const quizMockOf = (id: number): QuizMock => QUIZ_MOCKS[id] ?? QUIZ_MOCKS[1]

/** 목에서는 quizId 를 nodeId 와 같게 둔다 */
export const mockReviewQuiz = (nodeId: number): ReviewQuiz => {
  const item = reviewQueueMock.items.find((i) => i.nodeId === nodeId)
  const { kind, content } = quizMockOf(nodeId)
  return {
    quizId: nodeId,
    nodeId,
    concept: item?.concept ?? '개념',
    kind,
    content,
    guessP: 1 / content.options.length,
  }
}

export const mockReviewAnswer = (quizId: number, answer: number): ReviewResult => {
  const { key, explanation } = quizMockOf(quizId)
  const item = reviewQueueMock.items.find((i) => i.nodeId === quizId)
  const correct = answer === key
  const days = correct ? 11 : 1
  return {
    correct,
    key,
    explanation,
    concept: item?.concept ?? '개념',
    pKnow: correct ? 0.88 : 0.15,
    dueAt: new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString(),
  }
}
