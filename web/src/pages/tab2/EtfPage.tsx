import { Link, useSearchParams } from 'react-router'
import { useEtfDaily, useOverlaps } from '@/api/overlap'
import { ChangeRate } from '@/components/ChangeRate'
import { PageHeader } from '@/components/PageHeader'
import type { EtfMove } from '@/types/etf'
import type { Direction, StockOverlap } from '@/types/overlap'
import { DirectionChip } from './DirectionChip'
import { FilerChangeText } from './FilerChangeText'
import { daysBetween, etfShortName, filerShortName, formatDate, todayKst } from './labels'
import { ETF_UNIT_NOTE, FILING_DELAY_NOTE, GUIDE_NOTE, NO_OVERLAP_NOTE } from './notices'

type View = '13f' | 'etf'

/**
 * 탭2 메인: 상단 스위치로 "13F 공시"(겹침)와 "액티브 ETF"(어제 움직인 종목)를 오간다.
 * 선택한 쪽은 주소(?view=etf)에 남겨 종목 상세에서 뒤로 와도 그대로다.
 */
export const EtfPage = () => {
  const [params, setParams] = useSearchParams()
  const view: View = params.get('view') === 'etf' ? 'etf' : '13f'

  return (
    <div className="pb-6">
      <PageHeader />
      <div className="px-5">
        <div role="tablist" className="grid grid-cols-2 rounded-xl bg-slate-100 p-1">
          {(
            [
              ['13f', '13F 공시'],
              ['etf', '액티브 ETF'],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={view === key}
              onClick={() => setParams(key === 'etf' ? { view: 'etf' } : {}, { replace: true })}
              className={`min-h-11 rounded-lg text-sm font-semibold transition ${
                view === key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {view === '13f' ? <OverlapView /> : <EtfDailyView />}

      <div className="mx-5 mt-8 space-y-1.5 rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">
        <p>{GUIDE_NOTE}</p>
        <p>{view === '13f' ? FILING_DELAY_NOTE : ETF_UNIT_NOTE}</p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- 13F 공시 (겹침)

const OverlapView = () => {
  const { data, isPending, isError } = useOverlaps()

  if (isPending) return <StateText>불러오는 중…</StateText>
  if (isError)
    return <StateText>겹침 종목을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.</StateText>

  if (data.stocks.length === 0) {
    return <StateText>{NO_OVERLAP_NOTE}</StateText>
  }

  const periodEnd = data.stocks[0].filers[0]?.periodEnd
  const filedDates = data.stocks.flatMap((s) => s.filers.map((f) => f.filedAt)).filter(Boolean)
  const lastFiled = filedDates.length > 0 ? (filedDates.sort().at(-1) as string) : null

  return (
    <>
      <section className="mt-5 px-5">
        <h2 className="text-lg font-bold text-slate-900">큰손과 액티브 ETF가 겹친 종목</h2>
        <p className="mt-1 text-xs text-slate-500">
          {[
            periodEnd && `13F ${formatDate(periodEnd)} 기준`,
            lastFiled && `공시 후 ${daysBetween(lastFiled, todayKst())}일`,
          ]
            .filter(Boolean)
            .join(' · ')}
        </p>
        <ul className="mt-4 flex flex-col gap-3">
          {data.stocks.map((stock) => (
            <li key={stock.ticker}>
              <OverlapCard stock={stock} />
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-7 px-5">
        <h2 className="text-lg font-bold text-slate-900">분석</h2>
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 p-5 text-center text-sm text-slate-400">
          변동성 TOP2 분석 카드 준비 중
        </div>
      </section>
    </>
  )
}

const DIRECTIONS: Direction[] = ['same', 'diff', 'none']

const OverlapCard = ({ stock }: { stock: StockOverlap }) => {
  const counts = DIRECTIONS.map(
    (d) => [d, stock.pairs.filter((p) => p.direction === d).length] as const,
  ).filter(([, n]) => n > 0)

  return (
    <Link
      to={`/etf/${encodeURIComponent(stock.ticker)}`}
      className="block rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition active:scale-[0.99]"
    >
      <div className="flex items-baseline gap-2">
        <span className="text-lg font-bold text-slate-900">{stock.ticker}</span>
        <span className="truncate text-xs text-slate-500">
          {stock.issuerName ?? stock.etfStockName}
        </span>
        <span aria-hidden className="ml-auto text-slate-300">
          ›
        </span>
      </div>
      <ul className="mt-2 flex flex-col gap-1">
        {stock.filers.map((f) => (
          <li key={f.filerKey} className="flex items-center justify-between gap-2">
            <span className="text-sm text-slate-700">{filerShortName(f.filerKey)}</span>
            <FilerChangeText change={f} />
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-slate-500">
        액티브 ETF {stock.etfs.map((e) => etfShortName(e.etfCode)).join('·')} 보유
      </p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {counts.map(([d, n]) => (
          <DirectionChip key={d} direction={d} count={n} />
        ))}
      </div>
    </Link>
  )
}

// ---------------------------------------------------------------- 액티브 ETF (어제 변화)

const EtfDailyView = () => {
  const { data, isPending, isError } = useEtfDaily()

  if (isPending) return <StateText>불러오는 중…</StateText>
  if (isError)
    return <StateText>ETF 변화를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.</StateText>

  if (data.etfs.length === 0) {
    return <StateText>아직 액티브 ETF 보유 기록이 없어요.</StateText>
  }

  const dates = [...new Set(data.etfs.map((e) => e.snapshotDate))]
  const thresholdText = `${Math.round(data.threshold * 100)}%`

  return (
    <section className="mt-5 px-5">
      <h2 className="text-lg font-bold text-slate-900">어제 매니저들이 움직인 종목</h2>
      <p className="mt-1 text-xs text-slate-500">
        {data.etfs.map((e) => etfShortName(e.etfCode)).join('·')} ·{' '}
        {dates.map(formatDate).join(', ')} 기준 · 하루 {thresholdText} 이상 변화
      </p>

      <MoveSection title="두 ETF가 함께 늘림" emptyText="두 ETF가 함께 늘린 종목이 없어요.">
        {data.together.map((t) => (
          <li key={t.rawCode} className="flex min-h-12 items-center gap-2 py-2">
            <StockName ticker={t.ticker} name={t.stockName} />
            <span className="ml-auto flex flex-col items-end gap-0.5">
              {t.moves.map((m) => (
                <span key={m.etfCode} className="text-xs whitespace-nowrap">
                  <span className="mr-1 text-slate-500">{etfShortName(m.etfCode)}</span>
                  <ChangeRate value={m.dayChgPct} className="tabular-nums" />
                </span>
              ))}
            </span>
          </li>
        ))}
      </MoveSection>

      <MoveSection title="가장 많이 늘림" emptyText={`${thresholdText} 이상 늘린 종목이 없어요.`}>
        {data.topIncrease.map((m) => (
          <MoveRow key={`${m.etfCode}-${m.rawCode}`} move={m} />
        ))}
      </MoveSection>

      <MoveSection title="가장 많이 줄임" emptyText={`${thresholdText} 이상 줄인 종목이 없어요.`}>
        {data.topDecrease.map((m) => (
          <MoveRow key={`${m.etfCode}-${m.rawCode}`} move={m} />
        ))}
      </MoveSection>
    </section>
  )
}

const MoveSection = ({
  title,
  emptyText,
  children,
}: {
  title: string
  emptyText: string
  children: React.ReactNode[]
}) => {
  return (
    <div className="mt-4 rounded-2xl border border-slate-200 p-4">
      <h3 className="text-sm font-bold text-slate-900">{title}</h3>
      {children.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">{emptyText}</p>
      ) : (
        <ul className="mt-1 divide-y divide-slate-100">{children}</ul>
      )}
    </div>
  )
}

const MoveRow = ({ move }: { move: EtfMove }) => {
  return (
    <li className="flex min-h-12 items-center gap-2 py-2">
      <StockName ticker={move.ticker} name={move.stockName} />
      <span className="ml-auto flex items-center gap-2 whitespace-nowrap">
        <span className="text-xs text-slate-500">{etfShortName(move.etfCode)}</span>
        <ChangeRate value={move.dayChgPct} className="text-sm tabular-nums" />
      </span>
    </li>
  )
}

const StockName = ({ ticker, name }: { ticker: string | null; name: string | null }) => {
  return (
    <span className="min-w-0">
      <span className="block text-sm font-semibold text-slate-900">{ticker ?? name ?? '-'}</span>
      {ticker && name && <span className="block truncate text-xs text-slate-500">{name}</span>}
    </span>
  )
}

const StateText = ({ children }: { children: React.ReactNode }) => {
  return <p className="px-5 pt-6 text-sm leading-relaxed text-slate-500">{children}</p>
}
