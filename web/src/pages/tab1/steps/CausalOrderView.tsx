import { useState } from 'react'
import { useSubmitAnswer } from '@/api/cards'
import type { AnswerResult, CausalOrderStep } from '@/types/card'
import { AnswerFeedback } from '@/pages/tab1/steps/AnswerFeedback'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

interface CausalOrderViewProps {
  step: CausalOrderStep
  onNext: (result: AnswerResult) => void
}

/**
 * 인과 순서: 개념 칸을 원인부터 차례대로 누르면 번호가 붙는다 (UI 시안 12·13).
 * 정답은 사전 경로(서버)와 비교
 */
export const CausalOrderView = ({ step, onNext }: CausalOrderViewProps) => {
  const [order, setOrder] = useState<string[]>([])
  const submit = useSubmitAnswer()
  const result = submit.data
  const labelOf = (id: string) => step.items.find((item) => item.conceptId === id)?.label ?? id
  const full = order.length === step.items.length

  const toggle = (id: string) => {
    if (result) return
    setOrder(order.includes(id) ? order.filter((x) => x !== id) : [...order, id])
  }

  return (
    <StepFrame
      heading={step.question}
      buttonLabel={result ? '다음 ›' : '정답 확인'}
      buttonDisabled={!full || submit.isPending}
      onButton={() =>
        result
          ? onNext(result)
          : submit.mutate({ stepId: step.id, answer: { kind: 'causal_order', order } })
      }
    >
      <p className="text-sm text-slate-500">원인부터 차례대로 카드를 눌러 주세요.</p>

      <ul className="mt-4 flex flex-col gap-3">
        {step.items.map((item) => {
          const pos = order.indexOf(item.conceptId)
          return (
            <li key={item.conceptId}>
              <button
                type="button"
                disabled={!!result}
                onClick={() => toggle(item.conceptId)}
                className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-4 text-left font-semibold text-slate-900 transition ${
                  pos >= 0 ? 'border-primary bg-blue-50' : 'border-transparent bg-slate-100'
                }`}
              >
                <span
                  className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                    pos >= 0 ? 'bg-primary text-white' : 'bg-slate-300'
                  }`}
                >
                  {pos >= 0 ? pos + 1 : ''}
                </span>
                {item.label}
              </button>
            </li>
          )
        })}
      </ul>

      {!result && order.length > 0 && (
        <button
          type="button"
          onClick={() => setOrder([])}
          className="mt-4 min-h-11 text-sm text-slate-500 underline underline-offset-4"
        >
          다시 고르기
        </button>
      )}

      {result && (
        <AnswerFeedback
          result={result}
          correctText={
            Array.isArray(result.correct) ? result.correct.map(labelOf).join(' → ') : undefined
          }
        />
      )}
      {submit.isError && (
        <p className="text-up mt-3 text-sm">채점하지 못했어요. 다시 눌러 주세요.</p>
      )}
    </StepFrame>
  )
}
