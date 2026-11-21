import { useState } from 'react'
import { useSubmitAnswer } from '@/api/cards'
import type { AnswerResult, ChartStep as ChartStepData, PastAnswer, QuizStep } from '@/types/card'
import { AnswerFeedback, NotAnswered } from '@/pages/tab1/steps/AnswerFeedback'
import { ChartStep } from '@/pages/tab1/steps/ChartStep'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

interface QuizViewProps {
  step: QuizStep | ChartStepData
  onNext: (result?: AnswerResult) => void
  /** 퀴즈가 여러 개일 때 "퀴즈 1 / 2" */
  quizNo?: { no: number; total: number } | null
  /**
   * 풀었던 내용 보기(탭3). 있으면 그때 고른 보기와 채점 결과를 그대로 보여 주고 다시 채점하지 않는다.
   * null = 보기 모드인데 그날 이 문제를 안 풀었음. undefined = 평소처럼 푼다
   */
  past?: PastAnswer | null
}

const LETTERS = 'ABCDEFGH'

/** 간단 퀴즈와 차트 읽기(보기 고르기). 고르고 정답 확인 → 해설 → 다음 (UI 시안 09~11, 14) */
export const QuizView = ({ step, onNext, quizNo, past }: QuizViewProps) => {
  const reviewing = past !== undefined
  const pastPick =
    past?.input.kind === 'quiz' || past?.input.kind === 'chart' ? past.input.optionIndex : null
  const [picked, setPicked] = useState<number | null>(pastPick)
  const submit = useSubmitAnswer()
  const result = reviewing ? past?.result : submit.data

  const check = () => {
    if (picked === null) return
    submit.mutate({ stepId: step.id, answer: { kind: step.kind, optionIndex: picked } })
  }

  return (
    <StepFrame
      badge={quizNo && quizNo.total > 1 ? `퀴즈 ${quizNo.no} / ${quizNo.total}` : undefined}
      heading={step.question}
      buttonLabel={result || reviewing ? '다음 ›' : '정답 확인'}
      buttonDisabled={!reviewing && (picked === null || submit.isPending)}
      onButton={() => (reviewing ? onNext(past?.result) : result ? onNext(result) : check())}
    >
      {step.kind === 'chart' && <ChartStep chart={step.chart} ticker={step.ticker} />}
      <ul className="flex flex-col gap-3">
        {step.options.map((option, i) => (
          <li key={option}>
            <button
              type="button"
              disabled={!!result || reviewing}
              onClick={() => setPicked(i)}
              className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-4 text-left font-semibold transition ${optionClass(i, picked, result)}`}
            >
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-white text-sm font-bold text-slate-600">
                {LETTERS[i]}
              </span>
              {option}
            </button>
          </li>
        ))}
      </ul>
      {past === null && <NotAnswered />}
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

/** 고르기 전·후 보기 색. 결과가 나오면 정답은 파랑, 내가 고른 오답은 빨강 테두리 */
const optionClass = (i: number, picked: number | null, result?: AnswerResult) => {
  if (result) {
    if (i === result.correct) return 'border-primary bg-blue-50 text-slate-900'
    if (i === picked) return 'border-up bg-rose-50 text-slate-900'
    return 'border-transparent bg-slate-100 text-slate-400'
  }
  return i === picked
    ? 'border-primary bg-blue-50 text-slate-900'
    : 'border-transparent bg-slate-100 text-slate-800'
}
