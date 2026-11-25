import type { TutorGradedEvent } from '@/types/tutor'
import { AnswerFeedback } from '@/pages/tab1/steps/AnswerFeedback'

interface TutorFeedbackProps {
  graded: TutorGradedEvent
  /** 틀렸을 때 보여 줄 정답 (보기 글자). 칩 화면은 칸마다 정답을 표시하므로 비운다 */
  correctText?: string
}

/** 튜터 채점 결과를 간단 퀴즈와 같은 맞음·틀림 + 해설 칸으로 보여 준다 */
export const TutorFeedback = ({ graded, correctText }: TutorFeedbackProps) => (
  <AnswerFeedback
    result={{ stepId: 'tutor', isCorrect: graded.correct, explanation: graded.explanation }}
    correctText={correctText}
  />
)
