import { useState } from 'react'
import { useAnswerMeter } from '@/lib/answerMeter'
import type { AnswerMeta, Confidence } from '@/types/card'
import type {
  ChipBlankContent,
  MatchContent,
  SortContent,
  TutorChipKind,
  TutorGradedEvent,
} from '@/types/tutor'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'
import { TutorFeedback } from '@/pages/tab1/steps/TutorFeedback'

type ChipQuizProps = {
  badge: string
  graded?: TutorGradedEvent
  pending: boolean
  error: string | null
  onSubmit: (answer: number[], meta: AnswerMeta) => void
  onNext: () => void
} & (
  | { kind: '칩 빈칸'; content: ChipBlankContent }
  | { kind: '짝 맞추기'; content: MatchContent }
  | { kind: '사례 분류'; content: SortContent }
)

/** 칩 하나. value 는 서버에 보내는 번호 (짝 맞추기는 섞어 보여 줘도 원래 뜻 번호) */
interface Chip {
  text: string
  value: number
}

const BLANK = '___'

const HEADING: Record<TutorChipKind, string> = {
  '칩 빈칸': '빈칸에 알맞은 말을 넣어 주세요',
  '짝 맞추기': '용어마다 맞는 뜻을 넣어 주세요',
  '사례 분류': '사례를 알맞은 쪽에 넣어 주세요',
}

/** 짝 맞추기의 뜻은 용어 순서 그대로 오므로(정답이 늘 0,1,2) 화면에서 섞는다. 처음 한 번만 */
const shuffled = <T,>(xs: T[]): T[] => {
  const out = [...xs]
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

/**
 * 개념 단계 화면 B: 칩을 칸에 넣기 (칩 빈칸, 짝 맞추기, 사례 분류).
 * 칸을 누르면 고른 칸이 되고(처음엔 첫 빈칸), 아래 칩을 누르면 그 칸에 들어가고 다음 빈칸으로 넘어간다.
 * 채워진 칸을 다시 누르면 비운다. 칩 빈칸·짝 맞추기는 칩을 한 번만, 사례 분류는 바구니를 여러 번 쓴다.
 * 칸을 다 채우면 [헷갈려요]/[확실해요]로 낸다. 답은 칸 순서대로 칩 번호
 */
export const TutorChipQuiz = (props: ChipQuizProps) => {
  const { kind, badge, graded, pending, error, onSubmit, onNext } = props
  const [chips] = useState<Chip[]>(() => {
    if (props.kind === '칩 빈칸') return props.content.chips.map((text, value) => ({ text, value }))
    if (props.kind === '짝 맞추기')
      return shuffled(props.content.meanings.map((text, value) => ({ text, value })))
    return props.content.baskets.map((text, value) => ({ text, value }))
  })
  const slotCount =
    props.kind === '칩 빈칸'
      ? props.content.sentence.split(BLANK).length - 1
      : props.kind === '짝 맞추기'
        ? props.content.terms.length
        : props.content.cases.length
  const reusable = kind === '사례 분류'

  const [filled, setFilled] = useState<(number | null)[]>(() => Array(slotCount).fill(null))
  const [active, setActive] = useState<number | null>(0)
  const meter = useAnswerMeter()
  const key = Array.isArray(graded?.key) ? graded.key : null
  const locked = !!graded || pending

  const textOf = (value: number | null) => chips.find((c) => c.value === value)?.text ?? ''

  const tapChip = (value: number) => {
    if (locked || active === null) return
    const next = [...filled]
    // 답 바꾸기로 센다: 다른 칸에 있던 칩을 옮기거나(칩을 한 번만 쓰는 종류), 이미 찬 칸을 다른 칩으로 바꿀 때.
    // 둘이 한 번에 일어나도 한 번만 센다. 빈칸에 처음 넣는 것은 세지 않는다 (#243 리뷰)
    const was = reusable ? -1 : next.indexOf(value)
    const moved = was !== -1 && was !== active
    const replaced = next[active] !== null && next[active] !== value
    if (moved || replaced) meter.changed()
    if (was !== -1) next[was] = null // 다른 칸에 있던 칩은 옮긴다
    next[active] = value
    setFilled(next)
    const after = [...next.keys()].find((i) => i > active && next[i] === null)
    const first = next.indexOf(null)
    setActive(after ?? (first === -1 ? null : first))
  }

  const tapSlot = (i: number) => {
    if (locked) return
    if (filled[i] !== null) {
      meter.changed()
      setFilled(filled.map((v, j) => (j === i ? null : v)))
    }
    setActive(i)
  }

  const check = (confidence: Confidence) => {
    if (filled.every((v) => v !== null)) onSubmit(filled as number[], meter.read(confidence))
  }

  const slot = (i: number, placeholder: string, wide = false) => (
    <Slot
      key={i}
      text={filled[i] === null ? null : textOf(filled[i])}
      placeholder={placeholder}
      active={!locked && active === i}
      state={key ? (filled[i] === key[i] ? 'right' : 'wrong') : null}
      correctText={key && filled[i] !== key[i] ? textOf(key[i]) : null}
      disabled={locked}
      wide={wide}
      onClick={() => tapSlot(i)}
    />
  )

  return (
    <StepFrame
      badge={badge}
      heading={HEADING[kind]}
      buttonLabel="다음 ›"
      onButton={onNext}
      confidence={
        graded ? undefined : { disabled: filled.some((v) => v === null) || pending, onPick: check }
      }
    >
      {props.kind === '칩 빈칸' && (
        <p className="rounded-3xl bg-slate-50 px-5 py-5 text-lg leading-[2.4] font-semibold text-slate-800">
          {props.content.sentence.split(BLANK).map((part, i, parts) => (
            <span key={i}>
              {part}
              {i < parts.length - 1 && slot(i, '빈칸')}
            </span>
          ))}
        </p>
      )}
      {props.kind === '짝 맞추기' && (
        <ul className="flex flex-col gap-3">
          {props.content.terms.map((term, i) => (
            <li key={term} className="rounded-2xl bg-slate-50 px-4 py-3">
              <p className="mb-2 font-bold text-slate-900">{term}</p>
              {slot(i, '뜻 넣기', true)}
            </li>
          ))}
        </ul>
      )}
      {props.kind === '사례 분류' && (
        <ul className="flex flex-col gap-3">
          {props.content.cases.map((text, i) => (
            <li key={text} className="rounded-2xl bg-slate-50 px-4 py-3">
              <p className="mb-2 leading-relaxed text-slate-800">{text}</p>
              {slot(i, '어느 쪽?', true)}
            </li>
          ))}
        </ul>
      )}

      {!graded && (
        <div className="mt-5 flex flex-wrap gap-2" aria-label="넣을 칩">
          {chips.map((c) => {
            const used = !reusable && filled.includes(c.value)
            return (
              <button
                key={c.value}
                type="button"
                disabled={locked || active === null}
                onClick={() => tapChip(c.value)}
                className={`min-h-11 rounded-full border px-4 py-2 text-left text-sm font-semibold transition ${
                  used
                    ? 'border-slate-200 bg-white text-slate-300'
                    : 'border-primary text-primary bg-white active:scale-[0.98]'
                }`}
              >
                {c.text}
              </button>
            )
          })}
        </div>
      )}

      {graded && <TutorFeedback graded={graded} />}
      {error && <p className="text-up mt-3 text-sm">{error}</p>}
    </StepFrame>
  )
}

interface SlotProps {
  text: string | null
  placeholder: string
  active: boolean
  /** 채점 뒤: 맞은 칸 / 틀린 칸 */
  state: 'right' | 'wrong' | null
  /** 틀린 칸의 정답 */
  correctText: string | null
  disabled: boolean
  /** 칸이 한 줄을 다 쓴다 (짝 맞추기·사례 분류). 칩 빈칸은 문장 안에 들어간다 */
  wide: boolean
  onClick: () => void
}

const Slot = ({
  text,
  placeholder,
  active,
  state,
  correctText,
  disabled,
  wide,
  onClick,
}: SlotProps) => {
  const tone =
    state === 'right'
      ? 'border-primary bg-blue-50 text-slate-900'
      : state === 'wrong'
        ? 'border-up bg-rose-50 text-slate-900'
        : active
          ? 'border-primary border-dashed bg-white text-slate-400'
          : text
            ? 'border-slate-300 bg-white text-slate-900'
            : 'border-slate-300 border-dashed bg-white text-slate-400'
  return (
    <span className={wide ? 'block' : 'mx-1 inline-block align-middle'}>
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        aria-label={text ? `${text} (누르면 비워요)` : placeholder}
        className={`min-h-10 rounded-xl border-2 px-3 py-1 text-base leading-snug font-semibold transition ${tone} ${
          wide ? 'w-full text-left' : 'min-w-20'
        }`}
      >
        {text ?? placeholder}
      </button>
      {correctText && (
        <span className="text-primary mt-1 block text-sm leading-snug font-semibold">
          정답: {correctText}
        </span>
      )}
    </span>
  )
}
