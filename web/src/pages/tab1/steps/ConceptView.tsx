import type { ConceptStep } from '@/types/card'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

interface ConceptViewProps {
  step: ConceptStep
  onNext: () => void
}

/** 개념 학습: 설명 + 용어 카드. 채점 없음 */
export const ConceptView = ({ step, onNext }: ConceptViewProps) => {
  return (
    <StepFrame label="개념 학습" heading={step.title} buttonLabel="이해했어요 ›" onButton={onNext}>
      <p className="leading-relaxed text-slate-700">{step.body}</p>
      <dl className="mt-5 flex flex-col gap-2">
        {step.terms.map((t) => (
          <div key={t.term} className="rounded-2xl bg-slate-50 px-4 py-3">
            <dt className="text-sm font-bold text-slate-900">{t.term}</dt>
            <dd className="mt-0.5 text-sm text-slate-600">{t.desc}</dd>
          </div>
        ))}
      </dl>
    </StepFrame>
  )
}
