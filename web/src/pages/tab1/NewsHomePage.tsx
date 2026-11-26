import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useNewsHome, usePastNews } from '@/api/news'
import { SHOW_TAB2 } from '@/components/BottomNav'
import { Mate } from '@/components/Mate'
import { StockChartCard } from '@/pages/tab1/StockChartCard'
import type { NewsCardSummary, PastCard } from '@/types/news'

type View = 'all' | 'past'

const WEEKDAYS = '일월화수목금토'

/**
 * 탭1 뉴스 홈 (UI 시안 app.html 의 홈).
 * 위: 로고 · 검색 · 오늘의 트렌드(오늘 카드 순위를 한 줄씩 굴린다).
 * 가운데: [전체 | 지난 뉴스] · 오늘 주요뉴스(가로로 넘기는 카드).
 * 아래: 전체면 TOP 1 종목 차트 + O/X 퀴즈, 지난 뉴스면 지난 카드뉴스 목록.
 * 검색어를 넣으면 오늘·지난 카드의 제목·테마·요약에서 찾은 결과만 보여 준다.
 */
export const NewsHomePage = () => {
  const { data, isPending, isError } = useNewsHome()
  const past = usePastNews()
  const [view, setView] = useState<View>('all')
  const [searching, setSearching] = useState(false)
  const [query, setQuery] = useState('')

  if (isPending) {
    return <p className="text-sub p-5 text-sm font-semibold">불러오는 중…</p>
  }
  if (isError) {
    return (
      <p className="text-sub p-5 text-sm font-semibold">
        뉴스를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.
      </p>
    )
  }

  const completed = new Set([...data.completedCardIds, ...(past.data?.completedCardIds ?? [])])
  const pastCards = past.data?.cards ?? []
  const q = query.trim().toLowerCase()

  const toggleSearch = () => {
    setSearching(!searching)
    setQuery('')
  }

  return (
    <div className="pb-4">
      <header className="relative z-10 px-5 pt-[calc(12px+env(safe-area-inset-top))] pb-2.5">
        <div className="flex items-center gap-2">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <Mate className="size-[34px]" />
            <h1 className="mm-wordmark text-[21px]">MONEYMATE</h1>
          </div>
          <button
            type="button"
            onClick={toggleSearch}
            aria-label="뉴스 검색"
            aria-expanded={searching}
            className={`mm-round size-[42px] basis-[42px] ${searching ? 'border-blue bg-blue-soft' : ''}`}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              aria-hidden
            >
              <circle cx="11" cy="11" r="6.5" />
              <path d="M16 16l4.5 4.5" />
            </svg>
          </button>
        </div>
        {searching && (
          <label className="mt-2.5 block">
            <span className="sr-only">뉴스 검색</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
              autoComplete="off"
              placeholder="뉴스 제목이나 개념을 검색하세요"
              className="border-blue h-[46px] w-full rounded-[14px] border-2 px-3.5 text-base font-semibold outline-none"
            />
          </label>
        )}
        {data.cards.length > 0 && <TrendBar cards={data.cards} />}
      </header>

      {q ? (
        <SearchResults
          query={query.trim()}
          hits={[
            ...data.cards.map((card) => ({ card, date: null })),
            ...pastCards.map((p) => ({ card: p.card, date: p.date })),
          ].filter(({ card }) =>
            `${card.title} ${card.theme ?? ''} ${card.summary}`.toLowerCase().includes(q),
          )}
        />
      ) : (
        <>
          <div className="mm-pills px-5 pt-1.5" role="tablist" aria-label="보기 전환">
            <button
              type="button"
              role="tab"
              aria-selected={view === 'all'}
              onClick={() => setView('all')}
            >
              전체
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={view === 'past'}
              onClick={() => setView('past')}
            >
              지난 뉴스
            </button>
          </div>

          {data.cards.length > 0 ? (
            <TopNews cards={data.cards} completed={completed} />
          ) : (
            <div className="mm-empty">
              <Mate mood="think" />
              <p>오늘의 카드뉴스를 준비하고 있어요.</p>
            </div>
          )}

          {view === 'all' ? (
            data.stockChart && (
              <div className="mt-3 px-5">
                <StockChartCard chart={data.stockChart} />
              </div>
            )
          ) : (
            <section className="px-5">
              <div className="mm-h-sec">
                <h2>지난 카드뉴스</h2>
                {pastCards.length > 0 && <small>최근 {pastCards.length}건</small>}
              </div>
              {past.isPending && <p className="mm-none">불러오는 중…</p>}
              {past.isError && <p className="mm-none">지난 뉴스를 불러오지 못했어요.</p>}
              {past.data && pastCards.length === 0 && (
                <p className="mm-none">아직 지난 카드뉴스가 없어요.</p>
              )}
              <ul className="mm-plist">
                {pastCards.map((p) => (
                  <li key={p.card.id}>
                    <PastRow past={p} completed={completed.has(p.card.id)} />
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}

/** 한 줄씩 굴리는 간격 (ms) */
const ROLL_MS = 2800

/**
 * 오늘의 트렌드: 오늘 카드 순위(TOP 1, 2, …)를 한 줄씩 굴려 보여 주고, 누르면 전체 순위를 편다.
 * 순위는 서버가 준 카드 순서 그대로다 (화면이 다시 매기지 않는다).
 */
const TrendBar = ({ cards }: { cards: NewsCardSummary[] }) => {
  const [open, setOpen] = useState(false)
  const [at, setAt] = useState(0)

  useEffect(() => {
    if (open || cards.length < 2) return
    const timer = window.setInterval(() => setAt((i) => (i + 1) % cards.length), ROLL_MS)
    return () => window.clearInterval(timer)
  }, [open, cards.length])

  const current = cards[at % cards.length]

  return (
    <div className="border-line relative mt-2.5 rounded-[18px] border-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex h-[46px] w-full items-center gap-2.5 px-3 text-left text-[15px] font-extrabold"
      >
        <span className="mm-chip butter">오늘의 트렌드</span>
        <span className="relative h-[46px] min-w-0 flex-1 overflow-hidden">
          {/* key: 줄이 바뀔 때마다 아래에서 올라온다 */}
          <span key={current.id} className="mm-roll">
            <i>{(at % cards.length) + 1}</i>
            <span className="truncate">{current.title}</span>
          </span>
        </span>
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
          className={`text-sub shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <ol className="border-line absolute inset-x-[-2px] top-full mt-1.5 rounded-2xl border-2 bg-white p-1.5 shadow-[0_12px_28px_rgba(43,51,68,0.14)]">
          {cards.map((card, i) => (
            <li key={card.id}>
              <Link
                to={`/news/${card.id}`}
                className="active:bg-mist flex h-10 items-center gap-2.5 rounded-[10px] px-2 text-[15px] font-bold"
              >
                <i className="text-blue-ink min-w-3.5 font-extrabold not-italic">{i + 1}</i>
                <span className="truncate">{card.title}</span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

interface SearchResultsProps {
  query: string
  /** date 가 null 이면 오늘 카드, 있으면 지난 카드의 날짜 */
  hits: { card: NewsCardSummary; date: string | null }[]
}

const SearchResults = ({ query, hits }: SearchResultsProps) => (
  <section className="px-5">
    <div className="mm-h-sec">
      <h2>검색 결과</h2>
      <small>{hits.length}건</small>
    </div>
    {hits.length === 0 ? (
      <p className="mm-none">‘{query}’에 맞는 뉴스가 없어요. 다른 낱말로 검색해 보세요.</p>
    ) : (
      <ul className="mm-plist">
        {hits.map(({ card, date }) => (
          <li key={`${date ?? 'today'}:${card.id}`}>
            <Link to={`/news/${card.id}`} className="mm-box">
              <span className="tt">{card.title}</span>
              {card.theme && <span className="mm-chip">{card.theme}</span>}
            </Link>
          </li>
        ))}
      </ul>
    )}
  </section>
)

/** 지난 카드뉴스 한 줄: 날짜(일 + 요일) · 제목 · 배우기/학습 완료 */
const PastRow = ({ past, completed }: { past: PastCard; completed: boolean }) => {
  const [y, m, d] = past.date.split('-').map(Number)
  const weekday = WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]
  return (
    <Link
      to={`/news/${past.card.id}`}
      className="mm-box"
      aria-label={`${m}월 ${d}일 ${past.card.title}`}
    >
      <span className="dt">
        {d}
        <small>{weekday}</small>
      </span>
      <span className="tt">{past.card.title}</span>
      <span className={`mm-chip ${completed ? 'gray' : 'butter'}`}>
        {completed ? '학습 완료' : '배우기'}
      </span>
    </Link>
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
    const step = first.offsetWidth + 10 // gap-2.5
    setCurrent(Math.min(cards.length - 1, Math.max(0, Math.round(track.scrollLeft / step))))
  }

  return (
    <section>
      <div className="mm-h-sec mt-3.5 mb-2 px-5">
        <h2>오늘 주요뉴스</h2>
        <small>
          {current + 1} / {cards.length}
        </small>
      </div>

      <ol
        ref={trackRef}
        onScroll={onScroll}
        className="flex snap-x snap-mandatory scroll-px-5 gap-2.5 overflow-x-auto px-5 pt-0.5 pb-1.5"
      >
        {cards.map((card, i) => (
          <li key={card.id} className="w-[86%] shrink-0 snap-center">
            <NewsCard card={card} rank={i + 1} completed={completed.has(card.id)} />
          </li>
        ))}
      </ol>

      {cards.length > 1 && (
        <div aria-hidden className="mm-dots">
          {cards.map((card, i) => (
            <i key={card.id} className={i === current ? 'on' : ''} />
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
  return (
    <Link to={`/news/${card.id}`} className="mm-ncard">
      <span className="meta">
        <span className="mm-chip solid">TOP {rank}</span>
        {card.sourcePublishedAt && timeAgo(card.sourcePublishedAt)}
      </span>
      <strong>{card.title}</strong>
      <span className="foot">
        {card.theme && <span className="mm-chip gray">{card.theme}</span>}
        {SHOW_TAB2 && card.type === 3 && <span className="mm-chip butter">13F·ETF 연결</span>}
        {completed ? (
          <span className="mm-chip ok">학습 완료</span>
        ) : (
          <span className="mm-chip butter">배우기</span>
        )}
      </span>
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
