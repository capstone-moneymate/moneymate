import type { GhostReport } from '@/types/ghost'

/**
 * 고스트 비교 목 데이터 (가짜 기록). 실제로 어떻게 풀었는지와 상관없이 카드마다 같은 값을 돌려준다.
 * mock-rate-hold: 세 번째 시도. 퀴즈는 빨라졌고, 인과 순서는 처음 맞혔고, 판단 점수가 올랐다.
 */
export const ghostMocks: Record<string, GhostReport> = {
  'mock-rate-hold': {
    lastComplete: {
      attemptNo: 2,
      date: '2026-11-20',
      sureWrong: 1,
      steps: [
        { stepId: 'rh-2', kind: 'quiz', record: { isCorrect: true, seconds: 12, score: null } },
        {
          stepId: 'rh-3',
          kind: 'causal_order',
          record: { isCorrect: false, seconds: 40, score: null },
        },
        { stepId: 'rh-4', kind: 'chart', record: { isCorrect: true, seconds: 22, score: null } },
        {
          stepId: 'rh-5',
          kind: 'judgement',
          record: { isCorrect: false, seconds: null, score: 52 },
        },
      ],
    },
    comparison: {
      previous: { attemptNo: 2, date: '2026-11-20', sureWrong: 1 },
      current: { attemptNo: 3, date: '2026-11-24', sureWrong: 0 },
      improvedSteps: 3,
      rows: [
        {
          stepId: 'rh-2',
          kind: 'quiz',
          previous: { isCorrect: true, seconds: 12, score: null },
          current: { isCorrect: true, seconds: 5, score: null },
          improved: true,
          best: false,
        },
        {
          stepId: 'rh-3',
          kind: 'causal_order',
          previous: { isCorrect: false, seconds: 40, score: null },
          current: { isCorrect: true, seconds: 18, score: null },
          improved: true,
          best: true,
        },
        {
          stepId: 'rh-4',
          kind: 'chart',
          previous: { isCorrect: true, seconds: 22, score: null },
          current: { isCorrect: true, seconds: 25, score: null },
          improved: false,
          best: false,
        },
        {
          stepId: 'rh-5',
          kind: 'judgement',
          previous: { isCorrect: false, seconds: null, score: 52 },
          current: { isCorrect: true, seconds: null, score: 71 },
          improved: true,
          best: false,
        },
      ],
    },
  },
}
