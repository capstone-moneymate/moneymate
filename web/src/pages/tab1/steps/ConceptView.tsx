import { useState } from 'react'
import type { ConceptStep } from '@/types/card'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

interface ConceptViewProps {
  step: ConceptStep
  onNext: () => void
  /** 다음 단계 이름 (예: "간단 퀴즈"). 마지막 단계면 null */
  nextLabel: string | null
}

const MOODS = ['hi', 'think', 'smile', 'happy'] as const

/**
 * 개념 학습 (UI 시안 app.html 의 개념 칸): 말풍선에 제목, 아래에 용어 하나씩 큰 키워드 + 설명. 채점 없음.
 * 용어를 하나씩 넘기고, 마지막 용어에서 다음 단계로 간다. 위 칩을 눌러 다른 용어로 바로 갈 수도 있다
 */
export const ConceptView = ({ step, onNext, nextLabel }: ConceptViewProps) => {
  const [open, setOpen] = useState(0)
  const term = step.terms[open]
  const lastTerm = open >= step.terms.length - 1

  return (
    <StepFrame
      badge={step.terms.length > 0 ? `오늘의 개념 ${open + 1} / ${step.terms.length}` : '개념 학습'}
      heading={step.title}
      mood={MOODS[open % MOODS.length]}
      buttonLabel={lastTerm ? `이해했어요${nextLabel ? `, ${nextLabel}` : ''}` : '알겠어요'}
      onButton={() => (lastTerm ? onNext() : setOpen(open + 1))}
    >
      <p className="text-sub text-[15.5px] leading-relaxed font-medium">{step.body}</p>

      {term && (
        <>
          {step.terms.length > 1 && (
            <div className="mt-3.5 flex flex-wrap gap-2" role="tablist">
              {step.terms.map((t, i) => (
                <button
                  key={t.term}
                  type="button"
                  role="tab"
                  aria-selected={i === open}
                  onClick={() => setOpen(i)}
                  className={`h-9 rounded-full border-2 px-3.5 text-sm font-extrabold ${
                    i === open ? 'border-blue bg-blue text-white' : 'border-line text-sub bg-white'
                  }`}
                >
                  {t.term}
                </button>
              ))}
            </div>
          )}

          {/* key: 용어가 바뀌면 칸이 다시 들어온다 */}
          <article key={term.term} role="tabpanel" className="mm-box mm-concept">
            <span className="mm-chip gray">한 줄 개념</span>
            <h3 className="kw">{term.term}</h3>
            <p className="def">{term.desc}</p>
          </article>
        </>
      )}
    </StepFrame>
  )
}
