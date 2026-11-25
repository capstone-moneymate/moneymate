import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useCard, usePastAnswers } from '@/api/cards'
import { useGhost } from '@/api/ghost'
import { reviewLabel, useReviewDate, withReview } from '@/lib/review'
import { useLearnStore } from '@/store/learnStore'
import type { AnswerResult, PastAnswer, PastInput, Step } from '@/types/card'
import type { GhostAttempt } from '@/types/ghost'
import { LessonTop } from '@/pages/tab1/LessonTop'
import { CausalOrderView } from '@/pages/tab1/steps/CausalOrderView'
import { ConceptView } from '@/pages/tab1/steps/ConceptView'
import { QuizView } from '@/pages/tab1/steps/QuizView'
import { ReasonView } from '@/pages/tab1/steps/ReasonView'
import { TutorStep } from '@/pages/tab1/steps/TutorStep'

/**
 * 단계형 학습. 카드 유형에 따라 단계 구성이 다르다 (서비스흐름 2.2)
 * 유형 1: 개념 → 퀴즈 → 차트 → 판단 / 유형 2: 개념 → 퀴즈 → 인과 순서 → 차트 → 판단 / 유형 3: 개념 → 판단
 * AI 분석은 단계가 아니라 판단해보기 제출 후 결과 화면에 나온다
 * ?review=yyyy-MM-dd(탭3 풀었던 내용 보기)면 그날 낸 답과 채점 결과를 채운 채로 보여 주고 다시 채점하지 않는다
 * 개념 단계는 튜터 에이전트가 고른 설명·퀴즈로 진행한다 (추가구현_계획 1-3). 튜터를 못 쓰거나 풀었던 내용 보기면 기존 개념 설명.
 * 이전에 끝까지 푼 카드를 다시 풀면 단계마다 "지난번엔 맞혔어요"를 작게 보여 준다 (고스트 비교, 추가 구현 2-6).
 * 자세한 비교는 결과 화면에서 한다
 */
export const LearnPage = () => {
  const { cardId = '' } = useParams()
  const navigate = useNavigate()
  const { data: card, isPending, isError } = useCard(cardId)
  const review = useReviewDate()
  const past = usePastAnswers(cardId, review)
  // 풀기 시작할 때의 지난 기록. 못 불러와도 푸는 데는 지장이 없어서 기다리지 않는다
  const ghost = useGhost(cardId, 'learn', !review)
  const saveResult = useLearnStore((s) => s.saveResult)
  const resetCard = useLearnStore((s) => s.resetCard)
  const [index, setIndex] = useState(0)
  // 이번에 푼 단계의 답과 채점 결과. 뒤로 가면 다시 풀지 않고 푼 상태 그대로 보여 준다 (다시 제출하지 않는다)
  const [answered, setAnswered] = useState<Record<string, PastAnswer>>({})
  /** 지금까지 가 본 가장 뒤 단계 */
  const [reached, setReached] = useState(0)

  // 처음부터 다시 풀면 이전 기록을 지운다. 풀었던 내용 보기면 그날 채점 결과로 채워 결과 화면이 읽게 한다
  useEffect(() => {
    resetCard(cardId)
    past.data?.forEach((p) => saveResult(cardId, p.result))
  }, [cardId, resetCard, saveResult, past.data])

  if (isPending || (review && past.isPending))
    return <p className="text-sub p-5 text-sm font-semibold">불러오는 중…</p>
  if (isError) {
    return (
      <p className="text-sub p-5 text-sm font-semibold">
        카드를 찾을 수 없어요.{' '}
        <Link to="/" className="text-blue-ink underline">
          뉴스 홈으로
        </Link>
      </p>
    )
  }

  const step = card.steps[index]
  const next = (result?: AnswerResult, input?: PastInput) => {
    if (result) saveResult(card.id, result)
    if (result && input) setAnswered({ ...answered, [step.id]: { stepId: step.id, input, result } })
    if (index === card.steps.length - 1) navigate(withReview(`/news/${card.id}/result`, review))
    else {
      setIndex(index + 1)
      setReached(Math.max(reached, index + 1))
    }
  }
  // 뒤로: 앞 단계가 있으면 그 단계로(푼 상태 그대로), 첫 단계면 카드뉴스로
  const back = () =>
    index > 0 ? setIndex(index - 1) : navigate(withReview(`/news/${card.id}`, review))

  const nextStep = card.steps[index + 1]
  // 퀴즈가 여러 개면 "퀴즈 1 / 2" 표시
  const quizzes = card.steps.filter((s) => s.kind === 'quiz')
  const quizNo =
    step.kind === 'quiz' ? { no: quizzes.indexOf(step) + 1, total: quizzes.length } : null
  const lastTime = ghostLine(ghost.data?.lastComplete ?? null, step.id)
  // 진행 막대는 카드뉴스 장부터 이어서 센다 (CardNewsPage 와 같은 식)
  const slides = card.slides.length

  return (
    <div className="flex h-full flex-col">
      {/* UI 시안 app.html 의 학습 화면 위쪽: 닫기 · 뒤로 · 진행 막대 · 연속 학습 */}
      <LessonTop
        progress={((slides + index + 1) / (slides + card.steps.length)) * 100}
        onBack={back}
        backLabel={index > 0 ? '이전 단계로 돌아가기' : '카드뉴스로 돌아가기'}
      />
      {(review || lastTime) && (
        <p className="text-sub px-5 pb-1 text-xs font-semibold">
          {review && <b className="text-blue-ink">풀었던 내용 · {reviewLabel(review)}</b>}
          {review && lastTime && ' · '}
          {lastTime}
        </p>
      )}
      {/* key: 단계가 바뀌면 고른 답·입력을 새로 시작 */}
      <StepSwitch
        key={step.id}
        cardId={card.id}
        step={step}
        onNext={next}
        nextLabel={nextStep ? KIND_LABEL[nextStep.kind] : null}
        quizNo={quizNo}
        past={review ? (past.data?.find((p) => p.stepId === step.id) ?? null) : answered[step.id]}
        revisit={index < reached}
      />
    </div>
  )
}

/** 단계 이름 (개념 학습의 "이해했어요, ○○" 버튼) */
const KIND_LABEL: Record<Step['kind'], string> = {
  concept: '개념 학습',
  quiz: '간단 퀴즈',
  causal_order: '인과관계',
  chart: '차트 읽기',
  judgement: '판단해보기',
}

/** 지난번 이 단계의 기록 한 줄. 사실만 말한다. 기록이 없으면 null */
const ghostLine = (ghost: GhostAttempt | null, stepId: string): string | null => {
  const found = ghost?.steps.find((s) => s.stepId === stepId)
  if (!ghost || !found?.record) return null
  const last = `지난번(${reviewLabel(ghost.date)})`
  if (found.kind === 'judgement')
    return found.record.score === null ? null : `${last}엔 ${found.record.score}점이었어요`
  if (found.record.isCorrect === null) return null
  return `${last}엔 ${found.record.isCorrect ? '맞혔어요' : '틀렸어요'}`
}

interface StepSwitchProps {
  cardId: string
  step: Step
  onNext: (result?: AnswerResult, input?: PastInput) => void
  /** 다음 단계 이름. 마지막이면 null */
  nextLabel: string | null
  quizNo: { no: number; total: number } | null
  /** 그 단계에 이미 낸 답: 풀었던 내용 보기의 그날 답, 또는 이번에 풀고 뒤로 돌아온 단계의 답 (null = 안 풀었음, undefined = 지금 푼다) */
  past: PastAnswer | null | undefined
  /** 이미 지나간 단계로 돌아왔다 */
  revisit: boolean
}

const StepSwitch = ({
  cardId,
  step,
  onNext,
  nextLabel,
  quizNo,
  past,
  revisit,
}: StepSwitchProps) => {
  switch (step.kind) {
    case 'concept':
      // 풀었던 내용 보기에서는 튜터를 새로 열지 않는다 (그날의 튜터 세션은 남아 있지 않다).
      // 뒤로 돌아왔을 때도 튜터를 다시 시작하지 않고 개념 설명만 보여 준다
      if (past !== undefined || revisit)
        return <ConceptView step={step} onNext={onNext} nextLabel={nextLabel} />
      return <TutorStep cardId={cardId} step={step} onNext={onNext} nextLabel={nextLabel} />
    case 'quiz':
    case 'chart':
      return <QuizView step={step} onNext={onNext} quizNo={quizNo} past={past} />
    case 'causal_order':
      return <CausalOrderView step={step} onNext={onNext} past={past} />
    case 'judgement':
      return <ReasonView step={step} onNext={onNext} past={past} />
  }
}
