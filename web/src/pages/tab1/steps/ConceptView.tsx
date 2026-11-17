import { useState } from 'react'
import type { ConceptStep } from '@/types/card'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

interface ConceptViewProps {
  step: ConceptStep
  onNext: () => void
  /** 다음 단계 이름 (예: "간단 퀴즈"). 마지막 단계면 null */
  nextLabel: string | null
}

const CIRCLED = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨']

/**
 * 개념 학습: 설명 + 용어 탭(①②③…) + 고른 용어의 파란 설명 칸 (UI 시안 05~08). 채점 없음.
 * 용어를 하나씩 넘기고, 마지막 용어에서 다음 단계로 간다
 */
export const ConceptView = ({ step, onNext, nextLabel }: ConceptViewProps) => {
  const [open, setOpen] = useState(0)
  const term = step.terms[open]
  const lastTerm = open >= step.terms.length - 1

  return (
    <StepFrame
      heading={step.title}
      buttonLabel={
        lastTerm ? `이해했어요${nextLabel ? `, ${nextLabel}` : ''} ›` : '다음 개념 보기 ›'
      }
      onButton={() => (lastTerm ? onNext() : setOpen(open + 1))}
    >
      <p className="leading-relaxed text-slate-600">{step.body}</p>

      {step.terms.length > 0 && (
        <>
          <div className="mt-5 flex flex-wrap gap-2" role="tablist">
            {step.terms.map((t, i) => (
              <button
                key={t.term}
                type="button"
                role="tab"
                aria-selected={i === open}
                onClick={() => setOpen(i)}
                className={`min-h-11 rounded-full px-4 text-sm font-semibold transition ${
                  i === open ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {CIRCLED[i] ?? `${i + 1}.`} {t.term}
              </button>
            ))}
          </div>

          <div role="tabpanel" className="mt-4 rounded-3xl bg-blue-50 px-5 py-5">
            <span className="text-primary flex size-11 items-center justify-center rounded-xl bg-white">
              <BulbIcon />
            </span>
            <h3 className="mt-4 text-lg font-bold text-slate-900">{term.term}</h3>
            <p className="mt-2 leading-relaxed text-slate-700">{term.desc}</p>
          </div>
        </>
      )}
    </StepFrame>
  )
}

function BulbIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
    >
      <path
        d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1.1 2.2h5c.1-1 .5-1.7 1.1-2.2A6 6 0 0 0 12 3z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
