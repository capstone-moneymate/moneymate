import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useCard } from '@/api/cards'
import { useLearnStore } from '@/store/learnStore'
import type { AnswerResult, Step } from '@/types/card'
import { BackButton } from '@/pages/tab1/CloseLink'
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

  const total = card.steps.length
  const nextStep = card.steps[index + 1]
  // 퀴즈가 여러 개면 "퀴즈 1 / 2" 표시
  const quizzes = card.steps.filter((s) => s.kind === 'quiz')
  const quizNo =
    step.kind === 'quiz' ? { no: quizzes.indexOf(step) + 1, total: quizzes.length } : null

  return (
    <div className="flex min-h-full flex-col">
      {/* UI 시안 05~15: ‹ 뒤로 + "STEP n · 전체 · 단계 이름" + 단계 수만큼 막대 */}
      <div className="flex items-center gap-4 px-5 pt-4">
        <BackButton label="카드뉴스로 돌아가기" onClick={() => navigate(`/news/${card.id}`)} />
        <div>
          <p className="text-sm font-semibold text-slate-500">
            STEP {index + 1} · {total} · {KIND_LABEL[step.kind]}
          </p>
          <div className="mt-1.5 flex gap-1" aria-hidden>
            {card.steps.map((s, i) => (
              <span
                key={s.id}
                className={`h-1 w-6 rounded-full ${i <= index ? 'bg-primary' : 'bg-slate-200'}`}
              />
            ))}
          </div>
        </div>
      </div>
      <div className="flex flex-1 flex-col">
        {/* key: 단계가 바뀌면 고른 답·입력을 새로 시작 */}
        <StepSwitch
          key={step.id}
          step={step}
          onNext={next}
          nextLabel={nextStep ? KIND_LABEL[nextStep.kind] : null}
          quizNo={quizNo}
        />
      </div>
    </div>
  )
}

/** 단계 이름 (STEP 줄과 개념 학습의 "이해했어요, ○○ ›" 버튼) */
const KIND_LABEL: Record<Step['kind'], string> = {
  concept: '개념 학습',
  quiz: '간단 퀴즈',
  causal_order: '인과관계',
  chart: '차트 읽기',
  judgement: '판단해보기',
}

interface StepSwitchProps {
  step: Step
  onNext: (result?: AnswerResult) => void
  /** 다음 단계 이름. 마지막이면 null */
  nextLabel: string | null
  quizNo: { no: number; total: number } | null
}

const StepSwitch = ({ step, onNext, nextLabel, quizNo }: StepSwitchProps) => {
  switch (step.kind) {
    case 'concept':
      return <ConceptView step={step} onNext={onNext} nextLabel={nextLabel} />
    case 'quiz':
    case 'chart':
      return <QuizView step={step} onNext={onNext} quizNo={quizNo} />
    case 'causal_order':
      return <CausalOrderView step={step} onNext={onNext} />
    case 'judgement':
      return <ReasonView step={step} onNext={onNext} />
  }
}
