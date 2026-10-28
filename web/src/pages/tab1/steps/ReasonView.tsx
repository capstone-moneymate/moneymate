import { useState } from 'react'
import { useSubmitAnswer } from '@/api/cards'
import type { AnswerResult, JudgementStep, OpenEndedStep } from '@/types/card'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

/** 근거 최소 글자 수. 근거 작성은 필수 (기술확정안 루브릭) */
const MIN_REASON = 20

interface ReasonViewProps {
  step: JudgementStep | OpenEndedStep
  onNext: (result: AnswerResult) => void
}

/** 판단해보기(선택 + 근거)와 주관식(근거만). 선택은 채점하지 않고 근거만 루브릭으로 채점한다 */
export const ReasonView = ({ step, onNext }: ReasonViewProps) => {
  const [choice, setChoice] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const submit = useSubmitAnswer()
  const needsChoice = step.kind === 'judgement'
  const ready = (!needsChoice || choice !== null) && reason.trim().length >= MIN_REASON

  const send = () => {
    const answer =
      step.kind === 'judgement'
        ? { kind: 'judgement' as const, choiceIndex: choice ?? 0, reason: reason.trim() }
        : { kind: 'open_ended' as const, reason: reason.trim() }
    submit.mutate({ stepId: step.id, answer }, { onSuccess: onNext })
  }

  return (
    <StepFrame
      label={needsChoice ? '판단해보기' : '주관식'}
      heading={step.question}
      buttonLabel={submit.isPending ? '채점 중…' : '제출하기'}
      buttonDisabled={!ready || submit.isPending}
      onButton={send}
    >
      <p className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800">{step.context}</p>

      {step.kind === 'judgement' && (
        <ul className="mt-4 flex flex-col gap-2">
          {step.choices.map((c, i) => (
            <li key={c}>
              <button
                type="button"
                onClick={() => setChoice(i)}
                className={`w-full rounded-2xl border px-4 py-3.5 text-left text-sm ${
                  choice === i
                    ? 'border-primary text-primary bg-blue-50 font-semibold'
                    : 'border-slate-200 text-slate-800'
                }`}
              >
                {c}
              </button>
            </li>
          ))}
        </ul>
      )}

      <label className="mt-4 block">
        <span className="text-sm font-semibold text-slate-700">근거</span>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={5}
          placeholder="자료 속 숫자와 오늘 배운 개념을 이어서 써 보세요. 반대로 움직일 수 있는 이유도 있으면 좋아요."
          className="focus:border-primary mt-1.5 w-full resize-none rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none"
        />
        <span className="text-xs text-slate-400">
          {reason.trim().length} / 최소 {MIN_REASON}자
        </span>
      </label>
      {submit.isError && (
        <p className="text-up mt-2 text-sm">채점하지 못했어요. 다시 눌러 주세요.</p>
      )}
    </StepFrame>
  )
}
