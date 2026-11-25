import type { TutorAnswer, TutorEvent, TutorQuizEvent, TutorState } from '@/types/tutor'

/**
 * 개념 단계 튜터 목 데이터 (가짜 값). 화면 A·B 7종류를 차례로 한 번씩 내고 끝난다.
 * 정답(key)은 서버처럼 퀴즈 이벤트에는 없고, 답을 낸 뒤 graded 에만 담는다.
 */
const SCRIPT: { quiz: TutorQuizEvent; key: number | number[]; explanation: string }[] = [
  {
    quiz: {
      type: 'quiz',
      kind: 'O/X',
      concept: '자사주 소각',
      content: {
        statement: '회사가 사들인 자기 주식을 없애면 발행주식 총수가 줄어든다.',
        options: ['O', 'X'],
      },
      guess_p: 0.5,
    },
    key: 0,
    explanation: '소각한 만큼 주식 수가 줄어 한 주가 차지하는 몫이 커져요.',
  },
  {
    quiz: {
      type: 'quiz',
      kind: '용어 뜻',
      concept: '발행주식 총수',
      content: {
        question: "'발행주식 총수'의 뜻으로 맞는 것은?",
        options: [
          '회사가 지금까지 발행해 남아 있는 주식의 전체 수',
          '하루 동안 거래된 주식의 수',
          '대주주가 가진 주식의 수',
        ],
      },
      guess_p: 0.333,
    },
    key: 0,
    explanation: '거래량이나 대주주 지분과는 다른 말이에요.',
  },
  {
    quiz: {
      type: 'quiz',
      kind: '헷갈리는 쌍',
      concept: 'PER',
      content: {
        question: '주가를 주당순이익으로 나눈 값은 어느 쪽일까요?',
        options: ['PER', 'PBR'],
      },
      guess_p: 0.5,
    },
    key: 0,
    explanation: 'PBR 은 주가를 주당순자산으로 나눈 값이에요.',
  },
  {
    quiz: {
      type: 'quiz',
      kind: '틀린 설명',
      concept: '자사주 소각',
      content: {
        question: '자사주 소각에 대한 설명 중 틀린 것은?',
        options: [
          '소각하면 발행주식 총수가 줄어든다',
          '주주에게 이익을 돌려주는 방법 중 하나다',
          '소각하면 회사의 매출이 늘어난다',
        ],
      },
      guess_p: 0.333,
    },
    key: 2,
    explanation: '소각은 주식 수를 바꿀 뿐 매출과는 관계가 없어요.',
  },
  {
    quiz: {
      type: 'quiz',
      kind: '칩 빈칸',
      concept: '자사주 소각',
      content: {
        sentence: '회사가 ___ 를 사들여 없애면 ___ 가 줄어든다.',
        chips: ['매출', '자기 주식', '발행주식 총수', '부채'],
      },
      guess_p: 0.083,
    },
    key: [1, 2],
    explanation: '사들인 자기 주식을 없애는 것이 소각이에요.',
  },
  {
    quiz: {
      type: 'quiz',
      kind: '짝 맞추기',
      concept: '주당순이익',
      content: {
        terms: ['주당순이익', '발행주식 총수', '자사주 소각'],
        meanings: [
          '순이익을 주식 수로 나눈 값',
          '회사가 발행해 남아 있는 주식의 전체 수',
          '회사가 사들인 자기 주식을 없애는 것',
        ],
      },
      guess_p: 0.167,
    },
    key: [0, 1, 2],
    explanation: '주식 수가 줄면 같은 순이익에서 주당순이익이 커져요.',
  },
  {
    quiz: {
      type: 'quiz',
      kind: '사례 분류',
      concept: '자사주 소각',
      content: {
        baskets: ['주식 수가 줄어든다', '주식 수가 그대로다'],
        cases: [
          '사들인 자기 주식을 없앴다',
          '사들인 자기 주식을 금고에 보관했다',
          '자사주를 매입한 뒤 모두 소각했다',
          '현금 배당을 했다',
        ],
      },
      guess_p: 0.063,
    },
    key: [0, 1, 0, 1],
    explanation: '없앤 경우만 발행주식 총수가 줄어요. 보관한 자사주는 그대로 남아 있어요.',
  },
]

const sessions = new Map<string, number>()

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))

const state = (sessionId: string, at: number, events: TutorEvent[]): TutorState => ({
  sessionId,
  status: at < SCRIPT.length ? 'waiting' : 'done',
  finishedBy: at < SCRIPT.length ? null : 'go_main',
  targets: ['자사주 소각', '발행주식 총수'],
  quizzes: Math.min(at + 1, SCRIPT.length),
  maxQuizzes: SCRIPT.length,
  events,
})

export const mockTutorStart = async (cardId: string): Promise<TutorState> => {
  await wait(600)
  const sessionId = `mock-${cardId}-${Date.now()}`
  sessions.set(sessionId, 0)
  return state(sessionId, 0, [
    {
      type: 'explain',
      concept: '자사주 소각',
      style: '예시 위주',
      text: '회사가 시장에서 자기 회사 주식을 사들인 뒤 아예 없애 버리는 것을 자사주 소각이라고 해요. 피자를 8조각에서 6조각으로 다시 자르면 한 조각이 커지는 것과 비슷해요.',
    },
    SCRIPT[0].quiz,
  ])
}

export const mockTutorAnswer = async (
  sessionId: string,
  answer: TutorAnswer,
): Promise<TutorState> => {
  await wait(600)
  const at = sessions.get(sessionId)
  if (at === undefined || at >= SCRIPT.length) throw new Error('기다리는 퀴즈가 없어요')
  const { quiz, key, explanation } = SCRIPT[at]
  const graded: TutorEvent = {
    type: 'graded',
    concept: quiz.concept,
    kind: quiz.kind,
    correct: JSON.stringify(answer) === JSON.stringify(key),
    key,
    explanation,
  }
  sessions.set(sessionId, at + 1)
  const next: TutorEvent =
    at + 1 < SCRIPT.length ? SCRIPT[at + 1].quiz : { type: 'done', by: 'go_main' }
  return state(sessionId, at + 1, [graded, next])
}
