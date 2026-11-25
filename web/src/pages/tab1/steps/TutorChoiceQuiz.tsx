import { useState } from 'react'
import { useAnswerMeter } from '@/lib/answerMeter'
import type { AnswerMeta, Confidence } from '@/types/card'
import type { ChoiceContent, TutorChoiceKind, TutorGradedEvent } from '@/types/tutor'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'
import { TutorFeedback } from '@/pages/tab1/steps/TutorFeedback'

interface TutorChoiceQuizProps {
  kind: TutorChoiceKind
  content: ChoiceContent
  badge: string
  /** 채점 결과. 있으면 정답·내 답을 표시하고 [다음]만 보여 준다 */
  graded?: TutorGradedEvent
  pending: boolean
  error: string | null
  onSubmit: (answer: number, meta: AnswerMeta) => void
  onNext: () => void
}

const LETTERS = 'ABCDEFGH'

/** 문제 위 한 줄 안내. 화면에 보이는 종류 이름은 쓰지 않고 할 일만 말한다 */
const GUIDE: Record<TutorChoiceKind, string> = {
  '용어 뜻': '뜻이 맞는 것을 골라 주세요',
  '헷갈리는 쌍': '둘 중 맞는 쪽을 골라 주세요',
  '틀린 설명': '틀린 설명을 골라 주세요',
  'O/X': '맞으면 O, 틀리면 X',
}

/**
 * 개념 단계 화면 A: 보기 고르기 (용어 뜻, 헷갈리는 쌍, 틀린 설명, O/X).
 * 간단 퀴즈(QuizView)와 같은 모양: 고르고 [헷갈려요]/[확실해요] → 정답·해설 → 다음.
 * O/X 는 보기 두 개를 크게 나란히 둔다
 */
export const TutorChoiceQuiz = ({
  kind,
  content,
  badge,
  graded,
  pending,
  error,
  onSubmit,
  onNext,
}: TutorChoiceQuizProps) => {
  const [picked, setPicked] = useState<number | null>(null)
  const meter = useAnswerMeter()
  const key = typeof graded?.key === 'number' ? graded.key : null
  const ox = kind === 'O/X'

  const pick = (i: number) => {
    if (picked !== null && picked !== i) meter.changed()
    setPicked(i)
  }
  const check = (confidence: Confidence) => {
    if (picked !== null) onSubmit(picked, meter.read(confidence))
  }

  return (
    <StepFrame
      badge={badge}
      heading={content.question ?? content.statement ?? ''}
      buttonLabel="다음 ›"
      onButton={onNext}
      confidence={graded ? undefined : { disabled: picked === null || pending, onPick: check }}
    >
      <p className="-mt-2 mb-4 text-sm text-slate-500">{GUIDE[kind]}</p>
      <ul className={ox ? 'grid grid-cols-2 gap-3' : 'flex flex-col gap-3'}>
        {content.options.map((option, i) => (
          <li key={option}>
            <button
              type="button"
              disabled={!!graded || pending}
              onClick={() => pick(i)}
              aria-pressed={picked === i}
              className={`flex w-full items-center gap-3 rounded-2xl border font-semibold transition ${
                ox ? 'justify-center py-7 text-3xl' : 'px-4 py-4 text-left'
              } ${optionClass(i, picked, key)}`}
            >
              {!ox && (
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-white text-sm font-bold text-slate-600">
                  {LETTERS[i]}
                </span>
              )}
              {option}
            </button>
          </li>
        ))}
      </ul>
      {graded && (
        <TutorFeedback
          graded={graded}
          correctText={key !== null ? content.options[key] : undefined}
        />
      )}
      {error && <p className="text-up mt-3 text-sm">{error}</p>}
    </StepFrame>
  )
}

/** 고르기 전·후 보기 색. 채점되면 정답은 파랑, 내가 고른 오답은 빨강 테두리 (QuizView 와 같다) */
const optionClass = (i: number, picked: number | null, key: number | null) => {
  if (key !== null) {
    if (i === key) return 'border-primary bg-blue-50 text-slate-900'
    if (i === picked) return 'border-up bg-rose-50 text-slate-900'
    return 'border-transparent bg-slate-100 text-slate-400'
  }
  return i === picked
    ? 'border-primary bg-blue-50 text-slate-900'
    : 'border-transparent bg-slate-100 text-slate-800'
}
