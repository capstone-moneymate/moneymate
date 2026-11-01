import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useCard } from '@/api/cards'
import { CloseLink } from '@/pages/tab1/CloseLink'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

/** 카드뉴스: 2~3장을 스토리처럼 넘긴 뒤 단계형 학습으로 들어간다 (서비스흐름 2.1) */
export const CardNewsPage = () => {
  const { cardId = '' } = useParams()
  const navigate = useNavigate()
  const { data: card, isPending, isError } = useCard(cardId)
  const [index, setIndex] = useState(0)

  if (isPending) return <p className="p-5 text-sm text-slate-500">불러오는 중…</p>
  if (isError) {
    return (
      <div className="p-5 text-sm text-slate-500">
        카드를 찾을 수 없어요.{' '}
        <Link to="/" className="text-primary">
          뉴스 홈으로
        </Link>
      </div>
    )
  }

  const slide = card.slides[index]
  const isLast = index === card.slides.length - 1

  return (
    <div className="flex min-h-full flex-col">
      <div className="flex items-center gap-3 px-5 pt-5">
        {/* 장 수만큼 막대. 지난 장과 지금 장은 파랗게 */}
        <div className="flex flex-1 gap-1" aria-label={`${index + 1} / ${card.slides.length}장`}>
          {card.slides.map((s, i) => (
            <span
              key={s.label}
              className={`h-1 flex-1 rounded-full ${i <= index ? 'bg-primary' : 'bg-slate-200'}`}
            />
          ))}
        </div>
        <CloseLink />
      </div>

      <p className="px-5 pt-4 text-sm font-semibold text-slate-500">{card.title}</p>

      <div className="flex flex-1 flex-col">
        <StepFrame
          label={`${index + 1} · ${slide.label}`}
          heading={slide.heading}
          buttonLabel={isLast ? '학습 시작하기 ›' : '다음 카드 ›'}
          onButton={() => (isLast ? navigate(`/news/${card.id}/learn`) : setIndex(index + 1))}
        >
          <p className="leading-relaxed text-slate-700">{slide.body}</p>
          {slide.facts && (
            <dl className="mt-5 rounded-2xl bg-slate-50 px-4 py-2">
              {slide.facts.map((fact) => (
                <div key={fact.label} className="flex justify-between py-2 text-sm">
                  <dt className="text-slate-600">{fact.label}</dt>
                  <dd className={`font-semibold tabular-nums ${factColor(fact.value)}`}>
                    {fact.value}
                  </dd>
                </div>
              ))}
            </dl>
          )}
          {index > 0 && (
            <button
              type="button"
              onClick={() => setIndex(index - 1)}
              className="mt-5 text-sm text-slate-500"
            >
              ‹ 이전 카드
            </button>
          )}
        </StepFrame>
      </div>

      <p className="px-5 pb-4 text-center text-xs text-slate-400">
        출처{' '}
        <a href={card.sourceUrl} target="_blank" rel="noreferrer" className="underline">
          {card.sourceName}
        </a>{' '}
        · 카드 문장은 AI가 쓰고 숫자는 원자료로 계산했어요
      </p>
    </div>
  )
}

/** 상승 빨강 ▲, 하락 파랑 ▼ (ChangeRate 와 같은 규칙) */
const factColor = (value: string) => {
  if (value.startsWith('▲')) return 'text-up'
  if (value.startsWith('▼')) return 'text-down'
  return 'text-slate-900'
}
