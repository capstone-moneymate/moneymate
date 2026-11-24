import type { Calibration, CalibrationSummary, ReviewQueue } from '@/types/learner'

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
