import { useState } from 'react'
import { useSubmitAnswer } from '@/api/cards'
import type { AnswerResult, ChartStep as ChartStepData, QuizStep } from '@/types/card'
import { AnswerFeedback } from '@/pages/tab1/steps/AnswerFeedback'
import { ChartStep } from '@/pages/tab1/steps/ChartStep'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

interface QuizViewProps {
  step: QuizStep | ChartStepData
  onNext: (result: AnswerResult) => void
}

/** 간단 퀴즈와 차트 읽기(보기 고르기). 고르고 확인 → 해설 → 다음 */
export const QuizView = ({ step, onNext }: QuizViewProps) => {
  const [picked, setPicked] = useState<number | null>(null)
  const submit = useSubmitAnswer()
  const result = submit.data

  const check = () => {
    if (picked === null) return
    submit.mutate({ stepId: step.id, answer: { kind: step.kind, optionIndex: picked } })
  }

  return (
    <StepFrame
      label={step.kind === 'chart' ? '차트 읽기' : '간단 퀴즈'}
      heading={step.question}
      buttonLabel={result ? '다음 ›' : '확인'}
      buttonDisabled={picked === null || submit.isPending}
      onButton={() => (result ? onNext(result) : check())}
    >
      {step.kind === 'chart' && <ChartStep stepId={step.id} ticker={step.ticker} />}
      <ul className="flex flex-col gap-2">
        {step.options.map((option, i) => (
          <li key={option}>
            <button
              type="button"
              disabled={!!result}
              onClick={() => setPicked(i)}
              className={`w-full rounded-2xl border px-4 py-3.5 text-left text-sm transition ${optionClass(i, picked, result)}`}
            >
              {option}
            </button>
          </li>
        ))}
      </ul>
      {result && (
        <AnswerFeedback
          result={result}
          correctText={
            typeof result.correct === 'number' ? step.options[result.correct] : undefined
          }
        />
      )}
      {submit.isError && (
        <p className="text-up mt-3 text-sm">채점하지 못했어요. 다시 눌러 주세요.</p>
      )}
    </StepFrame>
  )
}

const optionClass = (i: number, picked: number | null, result?: AnswerResult) => {
  if (result) {
    if (i === result.correct) return 'border-primary bg-blue-50 font-semibold text-primary'
    if (i === picked) return 'border-up bg-rose-50 text-up'
    return 'border-slate-200 text-slate-400'
  }
  return i === picked
    ? 'border-primary bg-blue-50 font-semibold text-primary'
    : 'border-slate-200 text-slate-800'
}
