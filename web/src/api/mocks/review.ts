import { causalMapMock } from '@/api/mocks/causalMap'
import type { Review, Summary } from '@/types/causalMap'

/**
 * 다시 보는 개념 목 데이터. 인과 지도 목 데이터에서 푼 개념(total > 0)만 골라
 * 서버(MypageService.review)와 같은 순서로 놓는다: 정답률 낮은 순 → 푼 횟수 적은 순 → id 순.
 * 정답률 비교는 서버처럼 교차 곱으로 한다 (소수 오차 없게).
 */
const learned = causalMapMock.nodes.filter((n) => n.total > 0)

export const reviewMock: Review = {
  concepts: [...learned]
    .sort(
      (a, b) =>
        a.correct * b.total - b.correct * a.total ||
        a.total - b.total ||
        (a.id < b.id ? -1 : a.id > b.id ? 1 : 0),
    )
    .map(({ id, name, theme, correct, total }) => ({
      id,
      name,
      theme,
      correct,
      total,
      accuracy: correct / total,
    })),
}

/** 홈 숫자 목 데이터 (가짜 값). 배운 개념 수만 인과 지도 목 데이터와 맞췄다 */
export const summaryMock: Summary = {
  streakDays: 7,
  studiedToday: true,
  conceptCount: learned.length,
  accuracy: 0.8,
  gradedCount: 60,
  judgementCount: 3,
}
