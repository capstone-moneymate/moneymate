import { useState } from 'react'
import { useSubmitAnswer } from '@/api/cards'
import type { AnswerResult, CausalOrderStep } from '@/types/card'
import { AnswerFeedback } from '@/pages/tab1/steps/AnswerFeedback'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

interface CausalOrderViewProps {
  step: CausalOrderStep
  onNext: (result: AnswerResult) => void
}

/** 인과 순서: 개념 칸을 힘이 전해지는 순서대로 누른다. 정답은 사전 경로(서버)와 비교 */
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
      label="인과 순서"
      heading={step.question}
      buttonLabel={result ? '다음 ›' : '확인'}
      buttonDisabled={!full || submit.isPending}
      onButton={() =>
        result
          ? onNext(result)
          : submit.mutate({ stepId: step.id, answer: { kind: 'causal_order', order } })
      }
    >
      {/* 고른 순서 (인과 뼈대) */}
      <div className="flex min-h-14 flex-wrap items-center gap-1.5 rounded-2xl bg-slate-50 px-3 py-3">
        {order.length === 0 && (
          <span className="text-sm text-slate-400">아래 칸을 순서대로 눌러 보세요</span>
        )}
        {order.map((id, i) => (
          <span key={id} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-slate-400">→</span>}
            <span className="border-primary text-primary rounded-lg border bg-white px-2.5 py-1 text-sm font-semibold">
              {labelOf(id)}
            </span>
          </span>
        ))}
      </div>

      <ul className="mt-4 flex flex-col gap-2">
        {step.items.map((item) => {
          const pos = order.indexOf(item.conceptId)
          return (
            <li key={item.conceptId}>
              <button
                type="button"
                disabled={!!result}
                onClick={() => toggle(item.conceptId)}
                className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-3.5 text-left text-sm ${
                  pos >= 0
                    ? 'border-primary text-primary bg-blue-50'
                    : 'border-slate-200 text-slate-800'
                }`}
              >
                <span
                  className={`flex size-6 items-center justify-center rounded-full text-xs font-bold ${
                    pos >= 0 ? 'bg-primary text-white' : 'bg-slate-100 text-slate-400'
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

      {result && (
        <AnswerFeedback
          result={result}
          correctText={
            Array.isArray(result.correct) ? result.correct.map(labelOf).join(' → ') : undefined
          }
        />
      )}
    </StepFrame>
  )
}
