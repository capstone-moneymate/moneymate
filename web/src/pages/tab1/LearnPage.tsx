import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useCard } from '@/api/cards'
import { useLearnStore } from '@/store/learnStore'
import type { AnswerResult, Step } from '@/types/card'
import { CloseLink } from '@/pages/tab1/CloseLink'
import { CausalOrderView } from '@/pages/tab1/steps/CausalOrderView'
import { ConceptView } from '@/pages/tab1/steps/ConceptView'
import { QuizView } from '@/pages/tab1/steps/QuizView'
import { ReasonView } from '@/pages/tab1/steps/ReasonView'

/**
 * 단계형 학습. 카드 유형에 따라 단계 구성이 다르다 (서비스흐름 2.2)
 * 유형 1: 개념 → 퀴즈 → 차트 → 판단 / 유형 2: 개념 → 퀴즈 → 인과 순서 → 차트 → 판단 / 유형 3: 개념 → 판단
 * AI 분석은 단계가 아니라 판단해보기 제출 후 결과 화면에 나온다
 */
export const LearnPage = () => {
  const { cardId = '' } = useParams()
  const navigate = useNavigate()
  const { data: card, isPending, isError } = useCard(cardId)
  const saveResult = useLearnStore((s) => s.saveResult)
  const resetCard = useLearnStore((s) => s.resetCard)
  const [index, setIndex] = useState(0)

  // 처음부터 다시 풀면 이전 기록을 지운다
  useEffect(() => resetCard(cardId), [cardId, resetCard])

  if (isPending) return <p className="p-5 text-sm text-slate-500">불러오는 중…</p>
  if (isError) {
    return (
      <p className="p-5 text-sm text-slate-500">
        카드를 찾을 수 없어요.{' '}
        <Link to="/" className="text-primary">
          뉴스 홈으로
        </Link>
      </p>
    )
  }

  const step = card.steps[index]
  const next = (result?: AnswerResult) => {
    if (result) saveResult(card.id, result)
    if (index === card.steps.length - 1) navigate(`/news/${card.id}/result`)
    else setIndex(index + 1)
  }

  return (
    <div className="flex min-h-full flex-col">
      <div className="flex items-center gap-3 px-5 pt-5">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-200">
          <div
            className="bg-primary h-full rounded-full transition-all"
            style={{ width: `${((index + 1) / card.steps.length) * 100}%` }}
          />
        </div>
        <span className="text-xs font-semibold text-slate-500 tabular-nums">
          {index + 1} / {card.steps.length}
        </span>
        <CloseLink />
      </div>
      <div className="flex flex-1 flex-col">
        {/* key: 단계가 바뀌면 고른 답·입력을 새로 시작 */}
        <StepSwitch key={step.id} step={step} onNext={next} />
      </div>
    </div>
  )
}

interface StepSwitchProps {
  step: Step
  onNext: (result?: AnswerResult) => void
}

const StepSwitch = ({ step, onNext }: StepSwitchProps) => {
  switch (step.kind) {
    case 'concept':
      return <ConceptView step={step} onNext={onNext} />
    case 'quiz':
    case 'chart':
      return <QuizView step={step} onNext={onNext} />
    case 'causal_order':
      return <CausalOrderView step={step} onNext={onNext} />
    case 'judgement':
      return <ReasonView step={step} onNext={onNext} />
  }
}
