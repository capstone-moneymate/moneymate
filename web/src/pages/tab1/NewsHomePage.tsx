import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { useNewsHome } from '@/api/news'
import { PageHeader } from '@/components/PageHeader'
import { StockChartCard } from '@/pages/tab1/StockChartCard'
import type { NewsCardSummary } from '@/types/news'

/** 탭1 뉴스 홈: 위에 오늘 주요뉴스(가로로 넘기는 카드), 아래에 TOP 1 종목 차트 + O/X 퀴즈 */
export const NewsHomePage = () => {
  const { data, isPending, isError } = useNewsHome()

  if (isPending) {
    return <p className="p-5 text-sm text-slate-500">불러오는 중…</p>
  }
  if (isError) {
    return (
      <p className="p-5 text-sm text-slate-500">
        뉴스를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.
      </p>
    )
  }

  const completed = new Set(data.completedCardIds)

  return (
    <div className="pb-6">
      <PageHeader />

      {data.cards.length > 0 && <TopNews cards={data.cards} completed={completed} />}

      {data.stockChart && (
        <div className="mt-5 px-5">
          <StockChartCard chart={data.stockChart} />
        </div>
      )}
    </div>
  )
}

interface TopNewsProps {
  cards: NewsCardSummary[]
  completed: Set<string>
}

/** 오늘 주요뉴스: 옆 카드가 살짝 보이게 가로로 넘긴다. 위에 "n / 전체", 아래 점 */
const TopNews = ({ cards, completed }: TopNewsProps) => {
  const trackRef = useRef<HTMLOListElement>(null)
  const [current, setCurrent] = useState(0)

  const onScroll = () => {
    const track = trackRef.current
    const first = track?.firstElementChild as HTMLElement | null
    if (!track || !first) return
    const step = first.offsetWidth + 12 // gap-3
    setCurrent(Math.min(cards.length - 1, Math.max(0, Math.round(track.scrollLeft / step))))
  }

  return (
    <section className="mt-2">
      <div className="flex items-baseline justify-between px-5">
        <h2 className="text-lg font-bold text-slate-900">오늘 주요뉴스</h2>
        <span className="text-sm text-slate-500 tabular-nums">
          <b className="text-slate-900">{current + 1}</b> / {cards.length}
        </span>
      </div>

      <ol
        ref={trackRef}
        onScroll={onScroll}
        className="mt-3 flex snap-x snap-mandatory scroll-px-5 gap-3 overflow-x-auto px-5 pb-1"
      >
        {cards.map((card, i) => (
          <li key={card.id} className="w-[85%] shrink-0 snap-start">
            <NewsCard card={card} rank={i + 1} completed={completed.has(card.id)} />
          </li>
        ))}
      </ol>

      {cards.length > 1 && (
        <div aria-hidden className="mt-3 flex justify-center gap-1.5">
          {cards.map((card, i) => (
            <span
              key={card.id}
              className={`h-1.5 rounded-full transition-all ${
                i === current ? 'w-5 bg-slate-800' : 'w-1.5 bg-slate-300'
              }`}
            />
          ))}
        </div>
      )}
    </section>
  )
}

interface NewsCardProps {
  card: NewsCardSummary
  rank: number
  completed: boolean
}

const NewsCard = ({ card, rank, completed }: NewsCardProps) => {
  const meta = [card.theme, card.sourcePublishedAt && timeAgo(card.sourcePublishedAt)]
    .filter(Boolean)
    .join(' · ')

  return (
    <Link
      to={`/news/${card.id}`}
      className="block h-full rounded-3xl border border-slate-100 bg-white px-4 py-4 shadow-[0_4px_20px_rgba(30,41,90,0.08)] transition active:scale-[0.99]"
    >
      <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <span className="text-primary rounded-md bg-blue-50 px-1.5 py-0.5 font-bold">
          TOP {rank}
        </span>
        {meta && <span>{meta}</span>}
        {card.type === 3 && (
          <span className="rounded-md bg-amber-50 px-1.5 py-0.5 font-semibold text-amber-700">
            13F·ETF 연결
          </span>
        )}
        {completed && (
          <span className="text-primary ml-auto rounded-md bg-blue-50 px-1.5 py-0.5 font-semibold">
            학습 완료
          </span>
        )}
      </div>
      <h3
        className={`mt-2 leading-snug font-bold break-keep ${completed ? 'text-slate-500' : 'text-slate-900'}`}
      >
        {card.title}
      </h3>
    </Link>
  )
}

/** 1차 자료 발표 시각 → "방금 전" / "N시간 전" / "N일 전" */
const timeAgo = (iso: string) => {
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 60) return '방금 전'
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`
  return `${Math.floor(hours / 24)}일 전`
}
