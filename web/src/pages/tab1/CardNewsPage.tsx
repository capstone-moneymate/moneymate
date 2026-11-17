import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useCard } from '@/api/cards'
import { CloseLink } from '@/pages/tab1/CloseLink'

/** 카드뉴스: 파란 화면에서 2~3장을 스토리처럼 넘긴 뒤 단계형 학습으로 들어간다 (서비스흐름 2.1, UI 시안 02~04) */
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
  const total = card.slides.length
  const isLast = index === total - 1

  return (
    <div className="bg-primary flex min-h-full flex-col px-6 pt-7 pb-6 text-white">
      {/* 장 수만큼 막대. 지난 장과 지금 장은 흰색 */}
      <div className="flex gap-1.5" aria-label={`${index + 1} / ${total}장`}>
        {card.slides.map((s, i) => (
          <span
            key={s.label}
            className={`h-1 flex-1 rounded-full ${i <= index ? 'bg-white' : 'bg-white/30'}`}
          />
        ))}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <span className="rounded-full bg-white/15 px-3 py-1.5 text-sm font-semibold">
          {[card.theme, `카드 ${index + 1} / ${total}`].filter(Boolean).join(' · ')}
        </span>
        <CloseLink tone="onBlue" />
      </div>

      {/* 본문은 화면 가운데 */}
      <div className="flex flex-1 flex-col justify-center py-8">
        <p className="text-sm text-white/80">{slide.label}</p>
        <h2 className="mt-3 text-3xl leading-tight font-bold whitespace-pre-line">
          {slide.heading}
        </h2>
        <p className="mt-4 leading-relaxed text-white/90">{slide.body}</p>
        {slide.facts && (
          <dl className="mt-6 rounded-2xl bg-white/10 px-5 py-2">
            {slide.facts.map((fact) => (
              <div key={fact.label} className="flex justify-between gap-3 py-3 text-sm">
                <dt className="text-white/80">{fact.label}</dt>
                <dd className="text-right font-bold tabular-nums">{fact.value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <button
          type="button"
          onClick={() => (isLast ? navigate(`/news/${card.id}/learn`) : setIndex(index + 1))}
          className="text-primary w-full rounded-2xl bg-white py-4 text-base font-bold transition active:scale-[0.99]"
        >
          {isLast ? '이해했어요, 개념 학습 시작 ›' : '다음 카드 ›'}
        </button>
        {index > 0 && (
          <button
            type="button"
            onClick={() => setIndex(index - 1)}
            className="text-sm text-white/80"
          >
            ‹ 이전 카드
          </button>
        )}
        <p className="text-center text-xs text-white/60">
          출처{' '}
          <a href={card.sourceUrl} target="_blank" rel="noreferrer" className="underline">
            {card.sourceName}
          </a>{' '}
          · 카드 문장은 AI가 쓰고 숫자는 원자료로 계산했어요
        </p>
      </div>
    </div>
  )
}
