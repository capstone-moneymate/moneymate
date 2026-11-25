import { useState } from 'react'
import axios from 'axios'
import { fetchTutor, useTutorAnswer, useTutorStart } from '@/api/tutor'
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
  // 답을 낸 뒤 응답을 못 받았다(연결 끊김·시간 초과·처리 중): 다시 내기 전에 서버 상태부터 맞춘다
  const [unsure, setUnsure] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [retryMsg, setRetryMsg] = useState<string | null>(null)
  const [lost, setLost] = useState(false)

  if (start.isPending) return <Waiting text="지금 아는 정도를 보고 첫 문제를 고르는 중이에요…" />
  const fallback = <ConceptView step={step} onNext={onNext} nextLabel={nextLabel} />
  // 시작할 때 모델이 실패하면 서버는 200 에 status 'error' 와 done 을 준다. 그때도 기존 개념 설명 (#243 리뷰)
  if (start.isError || start.data.status === 'error' || start.data.finishedBy === 'no_targets')
    return fallback

  const { sessionId, maxQuizzes } = start.data
  const firstCount = start.data.events.length
  const events = [...start.data.events, ...more]
  // 채점(graded)은 바로 앞 퀴즈 화면이 같이 보여 주므로 건너뛴다
  let here = at
  while (events[here]?.type === 'graded') here += 1
  const event = events[here]
  const quizNo = events.slice(0, here + 1).filter((e) => e.type === 'quiz').length
  const badge = `개념 퀴즈 ${quizNo} / ${maxQuizzes}`

  /**
   * 서버가 그 답을 받았는지 GET 으로 맞춰 본다. 받았으면 서버의 이벤트를 그대로 쓰고(다시 내지 않는다),
   * 아직 처리 중이면 끝날 때까지 기다리고, 안 받았으면 다시 낼 수 있게 한다.
   * 답에는 어느 퀴즈의 답인지가 없어서, 그냥 다시 내면 서버가 다음 퀴즈의 답으로 채점할 수 있다 (#243 리뷰)
   */
  const reconcile = async () => {
    setSyncing(true)
    setRetryMsg(null)
    try {
      let s = await fetchTutor(sessionId)
      for (let i = 0; s.status === 'running' && i < SYNC_TRIES; i++) {
        await wait(SYNC_WAIT_MS)
        s = await fetchTutor(sessionId)
      }
      if (s.status === 'running') {
        setRetryMsg('아직 채점하고 있어요. 잠시 뒤 다시 눌러 주세요.')
        return
      }
      setUnsure(false)
      const known = s.events.slice(firstCount)
      if (known.length > more.length) {
        setMore(known) // 서버는 답을 받았다
        answer.reset()
      } else setRetryMsg('채점하지 못했어요. 다시 눌러 주세요.')
    } catch (e) {
      if ([404, 503].includes(statusOf(e))) setLost(true)
      else setRetryMsg('연결이 불안정해요. 다시 눌러 주세요.')
    } finally {
      setSyncing(false)
    }
  }

  const submit = (value: TutorAnswer, meta: AnswerMeta) => {
    if (unsure) {
      void reconcile() // 앞의 답이 서버에 들어갔는지 모른다: 다시 내지 않고 먼저 맞춘다
      return
    }
    setRetryMsg(null)
    answer.mutate(
      { sessionId, answer: value, meta },
      {
        onSuccess: (s) => setMore((m) => [...m, ...s.events]),
        onError: (e) => {
          const code = statusOf(e)
          if (code === 404) setLost(true)
          else if (code === 400 || code === 422) setRetryMsg('채점하지 못했어요. 다시 눌러 주세요.')
          else {
            // 응답이 없음(연결 끊김·시간 초과), 409(처리 중이거나 이미 받음), 503(채점 서버가 시간을 넘김): 맞춰 본다
            setUnsure(true)
            void reconcile()
          }
        },
      },
    )
  }

  // 세션이 사라졌거나 채점 서버가 꺼졌다: 퀴즈 화면에 머물러도 답을 낼 수 없으니 여기서 끝낸다
  if (lost) return fallbackEnd(onNext)
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
  const shared = {
    badge,
    graded,
    pending: answer.isPending || syncing,
    error: graded ? null : retryMsg,
    onNext: () => setAt(here + 2),
  }
  if (event.type !== 'quiz') return null
  return <QuizScreen key={here} event={event} shared={shared} submit={submit} />
}

/** 서버가 그 답을 받았는지 맞춰 볼 때, 아직 처리 중(running)이면 이만큼 기다렸다 다시 본다 (최대 약 90초) */
const SYNC_TRIES = 30
const SYNC_WAIT_MS = 3_000
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))

/** HTTP 상태. 응답 자체가 없으면(연결 끊김·시간 초과) 0 */
const statusOf = (e: unknown) => (axios.isAxiosError(e) ? (e.response?.status ?? 0) : 0)

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
    const chipProps = { ...shared, concept: event.concept, onSubmit: submit }
    if (event.kind === '칩 빈칸')
      return <TutorChipQuiz {...chipProps} kind={event.kind} content={event.content} />
    if (event.kind === '짝 맞추기')
      return <TutorChipQuiz {...chipProps} kind={event.kind} content={event.content} />
    return <TutorChipQuiz {...chipProps} kind={event.kind} content={event.content} />
  }
  if (!CHOICE_KINDS.includes(event.kind)) return null
  return <TutorChoiceQuiz {...shared} kind={event.kind} content={event.content} onSubmit={submit} />
}

/** 세션이 사라졌거나(서버 재시작 404) 채점 서버가 꺼졌을 때(503): 개념 단계를 여기서 끝낸다 */
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
