import { useState } from 'react'
import { useSubmitAnswer } from '@/api/cards'
import { DailyLimitError } from '@/api/client'
import type { AnswerResult, JudgementStep } from '@/types/card'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

/** 근거 최소 글자 수. 근거 작성은 필수 (기술확정안 루브릭) */
const MIN_REASON = 5

interface ReasonViewProps {
  step: JudgementStep
  onNext: (result: AnswerResult) => void
}

/** 판단해보기(선택 + 근거). 선택은 채점하지 않고 근거만 루브릭으로 채점한다 */
export const ReasonView = ({ step, onNext }: ReasonViewProps) => {
  const [choice, setChoice] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const submit = useSubmitAnswer()
  const ready = choice !== null && reason.trim().length >= MIN_REASON

  const limited = submit.error instanceof DailyLimitError ? submit.error.message : null

  const send = () => {
    if (choice === null) return
    const answer = {
      kind: 'judgement' as const,
      choiceIndex: choice,
      choice: step.choices[choice],
      reason: reason.trim(),
    }
    submit.mutate({ stepId: step.id, answer }, { onSuccess: onNext })
  }

  // 하루 채점 횟수를 다 쓰면 채점 없이 결과 화면으로 넘어간다 (결과 화면은 message 만 보여 준다)
  const skipGrading = (message: string) =>
    onNext({
      stepId: step.id,
      isCorrect: null,
      grade: {
        score: null,
        correct: null,
        rubric: null,
        reasons: {},
        grader: null,
        reused: false,
        message,
        feedback: null,
      },
    })

  return (
    <StepFrame
      buttonLabel={submit.isPending ? '채점 중…' : '제출하고 피드백 받기'}
      buttonDisabled={!ready || submit.isPending}
      onButton={send}
    >
      {/* UI 시안 15: "지금 당신이라면?" 칸에 질문, 안내(context)는 그 아래 작게 */}
      <div className="rounded-3xl bg-slate-100 px-5 py-5">
        <p className="text-sm text-slate-500">지금 당신이라면?</p>
        <h2 className="mt-2 text-lg leading-relaxed font-bold text-slate-900">{step.question}</h2>
      </div>
      {step.context && <p className="mt-2 px-1 text-sm text-slate-500">{step.context}</p>}

      {step.choices.length > 0 && (
        <>
          <p className="mt-5 text-sm font-semibold text-slate-700">나의 판단</p>
          <ul className="mt-2 flex flex-col gap-2">
            {step.choices.map((c, i) => (
              <li key={c}>
                <button
                  type="button"
                  onClick={() => setChoice(i)}
                  className={`w-full rounded-2xl px-4 py-4 text-left font-semibold transition ${
                    choice === i ? 'bg-primary text-white' : 'bg-slate-100 text-slate-800'
                  }`}
                >
                  {c}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      <label className="mt-5 block">
        <span className="text-sm font-semibold text-slate-700">
          판단 근거 <span className="text-up">(필수)</span>
        </span>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={5}
          placeholder="뉴스 속 사실과 오늘 배운 개념을 넣어서 이유를 써 보세요"
          className="focus:ring-primary mt-2 w-full resize-none rounded-3xl bg-slate-100 px-5 py-4 leading-relaxed outline-none focus:ring-2"
        />
      </label>
      <div className="mt-1 flex justify-between text-xs text-slate-400">
        <span className="tabular-nums">
          {reason.trim().length} / 최소 {MIN_REASON}자
        </span>
        <span>근거로 적용판단 점수를 매겨요</span>
      </div>
      {limited ? (
        <div className="mt-2 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
          <p>{limited}</p>
          <button
            type="button"
            onClick={() => skipGrading(limited)}
            className="text-primary mt-1.5 font-semibold"
          >
            채점 없이 결과 보기 ›
          </button>
        </div>
      ) : (
        submit.isError && (
          <p className="text-up mt-2 text-sm">채점하지 못했어요. 다시 눌러 주세요.</p>
        )
      )}
    </StepFrame>
  )
}
