import type { AnswerResult } from '@/types/card'

interface AnswerFeedbackProps {
  result: AnswerResult
  /** 틀렸을 때 보여 줄 정답 문장 */
  correctText?: string
}

/** 코드 채점 단계(퀴즈·인과 순서·차트)의 맞음·틀림 + 해설 */
export const AnswerFeedback = ({ result, correctText }: AnswerFeedbackProps) => {
  const ok = result.isCorrect === true
  return (
    <div role="status" className={`mt-5 rounded-2xl px-4 py-3 ${ok ? 'bg-blue-50' : 'bg-rose-50'}`}>
      <p className={`text-sm font-bold ${ok ? 'text-primary' : 'text-up'}`}>
        {ok ? '정답이에요' : '아쉬워요'}
      </p>
      {!ok && correctText && <p className="mt-1 text-sm text-slate-700">정답: {correctText}</p>}
      {result.explanation && <p className="mt-1 text-sm text-slate-600">{result.explanation}</p>}
    </div>
  )
}
