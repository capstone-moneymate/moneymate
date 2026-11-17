import type { AnswerResult } from '@/types/card'

interface AnswerFeedbackProps {
  result: AnswerResult
  /** 틀렸을 때 보여 줄 정답 문장 */
  correctText?: string
}

/** 코드 채점 단계(퀴즈·인과 순서·차트)의 맞음·틀림 + 해설 (UI 시안 10·13·14) */
export const AnswerFeedback = ({ result, correctText }: AnswerFeedbackProps) => {
  const ok = result.isCorrect === true
  return (
    <div role="status" className={`mt-5 rounded-3xl px-5 py-4 ${ok ? 'bg-blue-50' : 'bg-rose-50'}`}>
      <p className={`font-bold ${ok ? 'text-primary' : 'text-up'}`}>
        {ok ? '정답이에요' : '아쉬워요'}
      </p>
      {!ok && correctText && (
        <p className="mt-1.5 text-sm leading-relaxed text-slate-700">정답: {correctText}</p>
      )}
      {result.explanation && (
        <p className="mt-1.5 text-sm leading-relaxed text-slate-700">{result.explanation}</p>
      )}
    </div>
  )
}
