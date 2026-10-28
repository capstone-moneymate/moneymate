import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useCard } from '@/api/cards'
import { useLearnStore } from '@/store/learnStore'
import type { AnswerResult, Step } from '@/types/card'
import { CloseLink } from '@/pages/tab1/CloseLink'
import { AiAnalysis } from '@/pages/tab1/steps/AiAnalysis'
import { CausalOrderView } from '@/pages/tab1/steps/CausalOrderView'
import { ConceptView } from '@/pages/tab1/steps/ConceptView'
import { QuizView } from '@/pages/tab1/steps/QuizView'
import { ReasonView } from '@/pages/tab1/steps/ReasonView'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

/**
 * 단계형 학습. 카드 유형에 따라 단계 구성이 다르다 (서비스흐름 2.2)
 * 유형 1: 개념 → 퀴즈 → 차트 → 판단 / 유형 2: 개념 → 퀴즈 → 인과 순서 → 차트 → 판단 / 유형 3: 개념 → 주관식 → AI 분석
 */
export const LearnPage = () => {
  const { cardId = '' } = useParams()
  const navigate = useNavigate()
  const { data: card, isPending, isError } = useCard(cardId)
  const results = useLearnStore((s) => s.results[cardId])
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
        <StepSwitch key={step.id} step={step} steps={card.steps} results={results} onNext={next} />
      </div>
    </div>
  )
}

interface StepSwitchProps {
  step: Step
  steps: Step[]
  results?: Record<string, AnswerResult>
  onNext: (result?: AnswerResult) => void
}

const StepSwitch = ({ step, steps, results, onNext }: StepSwitchProps) => {
  switch (step.kind) {
    case 'concept':
      return <ConceptView step={step} onNext={onNext} />
    case 'quiz':
    case 'chart':
      return <QuizView step={step} onNext={onNext} />
    case 'causal_order':
      return <CausalOrderView step={step} onNext={onNext} />
    case 'judgement':
    case 'open_ended':
      return <ReasonView step={step} onNext={onNext} />
    case 'ai_analysis': {
      // 바로 앞 주관식의 채점 결과를 보여 준다
      const prev = steps[steps.indexOf(step) - 1]
      const grade = prev && results?.[prev.id]?.grade
      return (
        <StepFrame
          label="AI 분석"
          heading={'내 답을\n이렇게 읽었어요'}
          buttonLabel="결과 보기 ›"
          onButton={() => onNext()}
        >
          {grade ? (
            <AiAnalysis grade={grade} />
          ) : (
            <p className="text-sm text-slate-500">앞 단계 답안이 없어요.</p>
          )}
        </StepFrame>
      )
    }
  }
}
