import type { AnswerResult } from '@/types/card'
import type { TutorGradedEvent } from '@/types/tutor'

/** 튜터 채점 결과를 간단 퀴즈와 같은 맞음·틀림 + 해설 칸(StepFrame 의 feedback)으로 보여 주려고 모양을 맞춘다 */
export const tutorResult = (graded: TutorGradedEvent): AnswerResult => ({
  stepId: 'tutor',
  isCorrect: graded.correct,
  explanation: graded.explanation,
})
