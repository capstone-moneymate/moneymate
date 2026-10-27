import { Link } from 'react-router'
import { useNewsHome } from '@/api/news'
import { ChangeRate } from '@/components/ChangeRate'
import { PageHeader } from '@/components/PageHeader'
import { ProgressBar } from '@/components/ProgressBar'
import type { MarketIndex, NewsCardSummary } from '@/types/news'

/** 탭1 뉴스 홈: 주요 지수 + 오늘의 카드뉴스 3건 + 진행률 */
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
  const doneCount = data.cards.filter((card) => completed.has(card.id)).length

  return (
    <div className="pb-6">
      <PageHeader />

      <section className="px-5">
        <h2 className="sr-only">주요 지수</h2>
        <div className="grid grid-cols-2 gap-2">
          {data.indices.map((index) => (
            <IndexTile key={index.code} index={index} />
          ))}
        </div>
      </section>

      <section className="mt-7 px-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-bold text-slate-900">오늘의 카드뉴스</h2>
          <span className="text-xs text-slate-500">{formatDate(data.date)}</span>
        </div>
        <div className="mt-3">
          <ProgressBar done={doneCount} total={data.cards.length} />
        </div>

        <ol className="mt-4 flex flex-col gap-3">
          {data.cards.map((card, i) => (
            <li key={card.id}>
              <NewsCard card={card} order={i + 1} completed={completed.has(card.id)} />
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}

const IndexTile = ({ index }: { index: MarketIndex }) => {
  return (
    <div className="rounded-2xl bg-slate-50 px-4 py-3">
      <p className="text-xs text-slate-500">{index.name}</p>
      <p className="mt-0.5 text-base font-bold text-slate-900 tabular-nums">
        {index.value.toLocaleString('ko-KR', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}
      </p>
      <ChangeRate value={index.chgPct} className="text-xs tabular-nums" />
    </div>
  )
}

const TYPE_LABEL: Record<NewsCardSummary['type'], string> = {
  1: '개념 · 차트',
  2: '인과 뼈대',
  3: '종목 연결',
}

interface NewsCardProps {
  card: NewsCardSummary
  order: number
  completed: boolean
}

const NewsCard = ({ card, order, completed }: NewsCardProps) => {
  return (
    <Link
      to={`/news/${card.id}`}
      className={`block rounded-2xl border p-4 transition active:scale-[0.99] ${
        completed ? 'border-slate-200 bg-slate-50' : 'border-slate-200 bg-white shadow-sm'
      }`}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-primary text-sm font-bold">{order}</span>
        {card.theme && (
          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
            {card.theme}
          </span>
        )}
        <span className="text-xs text-slate-400">{TYPE_LABEL[card.type]}</span>
        <span className="ml-auto flex gap-1">
          {card.type === 3 && (
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
              13F·ETF 연결
            </span>
          )}
          {completed && (
            <span className="text-primary rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold">
              학습 완료
            </span>
          )}
        </span>
      </div>
      <h3
        className={`mt-2 leading-snug font-bold ${completed ? 'text-slate-500' : 'text-slate-900'}`}
      >
        {card.title}
      </h3>
      <p className="mt-1 line-clamp-2 text-sm text-slate-600">{card.summary}</p>
      <p className="mt-2 text-xs text-slate-400">
        {card.sourceName} · {formatTime(card.sourcePublishedAt)} · {card.stepCount}단계
      </p>
    </Link>
  )
}

/** '2026-10-09' → '10월 9일' */
const formatDate = (date: string) => {
  const [, month, day] = date.split('-').map(Number)
  return `${month}월 ${day}일`
}

/** UTC ISO 시각 → KST 'MM.DD HH:mm' */
const formatTime = (iso: string) => {
  return new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(iso))
}
