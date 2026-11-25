import { useState } from 'react'
import axios from 'axios'
import { useTutorAnswer, useTutorStart } from '@/api/tutor'
import type { ConceptStep } from '@/types/card'
import type { AnswerMeta } from '@/types/card'
import type { TutorAnswer, TutorEvent, TutorGradedEvent, TutorQuizEvent } from '@/types/tutor'
import { CHOICE_KINDS } from '@/types/tutor'
import { ConceptView } from '@/pages/tab1/steps/ConceptView'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'
import { TutorChipQuiz } from '@/pages/tab1/steps/TutorChipQuiz'
import { TutorChoiceQuiz } from '@/pages/tab1/steps/TutorChoiceQuiz'

interface TutorStepProps {
  cardId: string
  /** 튜터를 못 쓰면(채점 서버 꺼짐, 시간 초과, 목표 개념 없음) 이 개념 설명을 대신 보여 준다 */
  step: ConceptStep
  onNext: () => void
  nextLabel: string | null
}

/**
 * 개념 단계 (추가구현_계획 1-3): 튜터 에이전트가 지식 상태를 보고 설명과 퀴즈를 고른다.
 * 서버가 주는 이벤트(설명 → 퀴즈 → 채점 → … → 끝)를 하나씩 넘겨 보여 준다.
 * 퀴즈는 종류에 따라 화면 A(보기 고르기) 또는 화면 B(칩을 칸에 넣기). 답·확신·시간은 서버가 BKT 에 기록한다.
 * 시작이 실패하거나 목표 개념이 지도에 없으면(no_targets) 기존 개념 설명(ConceptView)으로 대신한다
 */
export const TutorStep = ({ cardId, step, onNext, nextLabel }: TutorStepProps) => {
  const start = useTutorStart(cardId)
  const answer = useTutorAnswer()
  const [more, setMore] = useState<TutorEvent[]>([])
  const [at, setAt] = useState(0)

  if (start.isPending) return <Waiting text="지금 아는 정도를 보고 첫 문제를 고르는 중이에요…" />
  const fallback = <ConceptView step={step} onNext={onNext} nextLabel={nextLabel} />
  if (start.isError || start.data.finishedBy === 'no_targets') return fallback

  const { sessionId, maxQuizzes } = start.data
  const events = [...start.data.events, ...more]
  // 채점(graded)은 바로 앞 퀴즈 화면이 같이 보여 주므로 건너뛴다
  let here = at
  while (events[here]?.type === 'graded') here += 1
  const event = events[here]
  const quizNo = events.slice(0, here + 1).filter((e) => e.type === 'quiz').length
  const badge = `개념 퀴즈 ${quizNo} / ${maxQuizzes}`

  // 세션이 사라졌다: 퀴즈 화면에 머물러도 답을 낼 수 없으니 여기서 끝낸다
  if (answer.isError && lostSession(answer.error)) return fallbackEnd(onNext)
  // 다음 이벤트가 아직 안 왔다: 답을 내고 다음 문제를 기다리는 중
  if (!event) return <Waiting text="다음 문제를 고르는 중이에요…" />

  if (event.type === 'explain') {
    return (
      <StepFrame heading={event.concept} buttonLabel="다음 ›" onButton={() => setAt(here + 1)}>
        <div className="rounded-3xl bg-blue-50 px-5 py-5">
          <p className="text-primary text-xs font-bold">{event.style}</p>
          <p className="mt-2 leading-relaxed text-slate-700">{event.text}</p>
        </div>
      </StepFrame>
    )
  }

  if (event.type === 'done')
    return <Done targets={start.data.targets} onNext={onNext} nextLabel={nextLabel} />

  // 퀴즈: 바로 다음 이벤트가 채점이면 결과를 표시한다
  const after = events[here + 1]
  const graded = after?.type === 'graded' ? after : undefined
  const submit = (value: TutorAnswer, meta: AnswerMeta) =>
    answer.mutate(
      { sessionId, answer: value, meta },
      { onSuccess: (s) => setMore((m) => [...m, ...s.events]) },
    )
  const error =
    answer.isError && !lostSession(answer.error) ? '채점하지 못했어요. 다시 눌러 주세요.' : null
  const shared = {
    badge,
    graded,
    pending: answer.isPending,
    error,
    onNext: () => setAt(here + 2),
  }
  if (event.type !== 'quiz') return null
  return <QuizScreen key={here} event={event} shared={shared} submit={submit} />
}

interface QuizScreenProps {
  event: TutorQuizEvent
  shared: {
    badge: string
    graded?: TutorGradedEvent
    pending: boolean
    error: string | null
    onNext: () => void
  }
  submit: (value: TutorAnswer, meta: AnswerMeta) => void
}

/** 종류에 따라 화면 A·B. key={here} 로 문제마다 고른 답·시간을 새로 시작한다 */
const QuizScreen = ({ event, shared, submit }: QuizScreenProps) => {
  if (event.kind === '칩 빈칸' || event.kind === '짝 맞추기' || event.kind === '사례 분류') {
    const chipProps = { ...shared, onSubmit: submit }
    if (event.kind === '칩 빈칸')
      return <TutorChipQuiz {...chipProps} kind={event.kind} content={event.content} />
    if (event.kind === '짝 맞추기')
      return <TutorChipQuiz {...chipProps} kind={event.kind} content={event.content} />
    return <TutorChipQuiz {...chipProps} kind={event.kind} content={event.content} />
  }
  if (!CHOICE_KINDS.includes(event.kind)) return null
  return <TutorChoiceQuiz {...shared} kind={event.kind} content={event.content} onSubmit={submit} />
}

/** 세션이 사라졌거나(서버 재시작 404) 채점 서버가 꺼졌다(503): 개념 단계를 여기서 끝낸다 */
const lostSession = (e: unknown) =>
  axios.isAxiosError(e) && [404, 409, 503].includes(e.response?.status ?? 0)

const fallbackEnd = (onNext: () => void) => (
  <StepFrame heading="개념 퀴즈를 이어 가지 못했어요" buttonLabel="다음 단계로 ›" onButton={onNext}>
    <p className="leading-relaxed text-slate-600">
      지금까지 푼 기록은 저장됐어요. 다음 단계로 넘어가요.
    </p>
  </StepFrame>
)

const Waiting = ({ text }: { text: string }) => (
  <div className="flex flex-1 flex-col items-center justify-center gap-4 px-5" role="status">
    <span className="border-primary size-9 animate-spin rounded-full border-4 border-t-transparent" />
    <p className="text-sm text-slate-500">{text}</p>
  </div>
)

const Done = ({
  targets,
  onNext,
  nextLabel,
}: {
  targets: string[]
  onNext: () => void
  nextLabel: string | null
}) => (
  <StepFrame
    heading="개념 퀴즈를 마쳤어요"
    buttonLabel={`이해했어요${nextLabel ? `, ${nextLabel}` : ''} ›`}
    onButton={onNext}
  >
    <p className="leading-relaxed text-slate-600">이 카드에서 쓰는 개념이에요.</p>
    <div className="mt-4 flex flex-wrap gap-2">
      {targets.map((t) => (
        <span
          key={t}
          className="text-primary rounded-full bg-blue-50 px-4 py-2 text-sm font-semibold"
        >
          {t}
        </span>
      ))}
    </div>
  </StepFrame>
)
