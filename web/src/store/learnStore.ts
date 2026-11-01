import { create } from 'zustand'
import type { AnswerResult } from '@/types/card'

/**
 * 카드별 단계 채점 결과. 결과 화면이 점수를 계산할 때 읽는다.
 * 새로고침하면 사라진다 (답안 기록은 서버 user_answers 가 원본이 될 예정).
 */
interface LearnState {
  results: Record<string, Record<string, AnswerResult>>
  saveResult: (cardId: string, result: AnswerResult) => void
  resetCard: (cardId: string) => void
}

export const useLearnStore = create<LearnState>((set) => ({
  results: {},
  saveResult: (cardId, result) =>
    set((state) => ({
      results: {
        ...state.results,
        [cardId]: { ...state.results[cardId], [result.stepId]: result },
      },
    })),
  resetCard: (cardId) =>
    set((state) => {
      const next = { ...state.results }
      delete next[cardId]
      return { results: next }
    }),
}))
