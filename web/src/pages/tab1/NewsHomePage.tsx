import { Link } from 'react-router'
import { useNewsHome } from '@/api/news'
import { ChangeRate } from '@/components/ChangeRate'
import { PageHeader } from '@/components/PageHeader'
import type { MarketIndex, NewsCardSummary } from '@/types/news'

/** 국내 지수 코드. 나머지(IXIC, US500)는 해외 */
const KR_INDEX = new Set(['KS11', 'KQ11'])

/** 탭1 뉴스 홈: 주요 지수 + 오늘의 카드뉴스 + 학습 수 (UI 시안 01) */
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
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-lg font-bold text-slate-900">주요 지수</h2>
          <span className="text-right text-xs text-slate-500">{closeNote(data.indices)}</span>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2.5">
          {data.indices.map((index) => (
            <IndexTile key={index.code} index={index} />
          ))}
        </div>
      </section>

      <section className="mt-7 px-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-bold text-slate-900">오늘의 카드뉴스</h2>
          <span className="text-sm text-slate-500 tabular-nums">
            {doneCount} / {data.cards.length} 학습
          </span>
        </div>

        <ol className="mt-3 flex flex-col gap-3">
          {data.cards.map((card) => (
            <li key={card.id}>
              <NewsCard card={card} completed={completed.has(card.id)} />
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}

const IndexTile = ({ index }: { index: MarketIndex }) => {
  return (
    <div className="rounded-2xl bg-slate-100 px-4 py-3.5">
      <p className="text-sm text-slate-500">{index.name}</p>
      <p className="mt-1 text-xl font-bold text-slate-900 tabular-nums">
        {index.value.toLocaleString('ko-KR', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}
      </p>
      <div className="mt-1">
        {index.chgPct === null ? (
          <span className="text-sm text-slate-400">-</span>
        ) : (
          <ChangeRate value={index.chgPct} className="text-sm tabular-nums" />
        )}
      </div>
    </div>
  )
}

interface NewsCardProps {
  card: NewsCardSummary
  completed: boolean
}

const NewsCard = ({ card, completed }: NewsCardProps) => {
  const meta = [card.theme, card.sourcePublishedAt && timeAgo(card.sourcePublishedAt)]
    .filter(Boolean)
    .join(' · ')

  return (
    <Link
      to={`/news/${card.id}`}
      className="block rounded-2xl bg-slate-100 px-4 py-4 transition active:scale-[0.99]"
    >
      <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
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
        className={`mt-2 leading-snug font-bold ${completed ? 'text-slate-500' : 'text-slate-900'}`}
      >
        {card.title}
      </h3>
    </Link>
  )
}

/** '2026-11-18' → '11/18' */
const shortDate = (date: string) => {
  const [, month, day] = date.split('-').map(Number)
  return `${month}/${day}`
}

/** "국내 11/18 마감 · 해외 11/17(현지시간) 마감". 지수마다 거래일이 다를 수 있어 시장별 가장 늦은 날 */
const closeNote = (indices: MarketIndex[]) => {
  const latest = (kr: boolean) =>
    indices
      .filter((i) => KR_INDEX.has(i.code) === kr)
      .map((i) => i.date)
      .sort()
      .at(-1)
  const kr = latest(true)
  const us = latest(false)
  return [kr && `국내 ${shortDate(kr)} 마감`, us && `해외 ${shortDate(us)}(현지시간) 마감`]
    .filter(Boolean)
    .join(' · ')
}

/** 1차 자료 발표 시각 → "방금 전" / "N시간 전" / "N일 전" */
const timeAgo = (iso: string) => {
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 60) return '방금 전'
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`
  return `${Math.floor(hours / 24)}일 전`
}
