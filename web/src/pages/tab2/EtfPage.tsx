import type { ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useEtfDaily, useOverlaps } from '@/api/overlap'
import { PageHeader } from '@/components/PageHeader'
import type { EtfMove } from '@/types/etf'
import type { StockOverlap } from '@/types/overlap'
import {
  daysBetween,
  etfShortName,
  FILERS,
  filerPersonName,
  isBigUp,
  quarterOf,
  shortDate,
  signedPct,
} from './labels'
import { ETF_NOTE, F13_NOTE, NO_OVERLAP_NOTE } from './notices'

type View = '13f' | 'etf'

/**
 * 탭2 메인 (시안 18·22): 상단 스위치로 "13F 공시"와 "액티브 ETF"를 오간다.
 * 선택한 쪽은 주소(?view=etf)에 남겨 종목 상세에서 뒤로 와도 그대로다.
 */
export const EtfPage = () => {
  const [params, setParams] = useSearchParams()
  const view: View = params.get('view') === 'etf' ? 'etf' : '13f'

  return (
    <div className="pb-6">
      <PageHeader />
      <div className="px-5">
        <div role="tablist" className="grid grid-cols-2 rounded-2xl bg-slate-100 p-1">
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
              className={`h-11 rounded-xl text-base font-bold transition ${
                view === key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {view === '13f' ? <OverlapView /> : <EtfDailyView />}
    </div>
  )
}

// ---------------------------------------------------------------- 13F 공시

/** 함께 늘렸다고 보는 최소 인원 (시안 18: "4명 중 2명 이상") */
const MIN_FILERS = 2

/** 13F 에서 새로 담았거나 +5% 이상 늘린 큰손 (worker 와 같은 기준) */
const raisedBy = (stock: StockOverlap) => stock.filers.filter(isBigUp)

const OverlapView = () => {
  const { data, isPending, isError } = useOverlaps()

  if (isPending) return <StateText>불러오는 중…</StateText>
  if (isError)
    return <StateText>13F 기록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.</StateText>

  // 많이 함께 늘린 순, 같으면 티커 순
  const together = data.stocks
    .map((stock) => ({ stock, raised: raisedBy(stock) }))
    .filter(({ raised }) => raised.length >= MIN_FILERS)
    .sort(
      (a, b) => b.raised.length - a.raised.length || a.stock.ticker.localeCompare(b.stock.ticker),
    )

  const periodEnd = data.stocks[0]?.filers[0]?.periodEnd
  const filed = data.stocks.flatMap((s) => s.filers.map((f) => f.filedAt)).filter(Boolean)
  const lastFiled = filed.length ? (filed.sort().at(-1) as string) : null

  return (
    <section className="mt-6 px-5">
      <h2 className="text-xl font-bold text-slate-900">
        {periodEnd ? `${quarterOf(periodEnd)} ` : ''}큰손들이 함께 늘린 종목
      </h2>
      <p className="mt-1.5 text-sm text-slate-500">
        {[
          periodEnd && `${shortDate(periodEnd)} 기준 기록`,
          periodEnd && lastFiled && `공시 D+${daysBetween(periodEnd, lastFiled)}`,
          `${FILERS.length}명 중 ${MIN_FILERS}명 이상`,
        ]
          .filter(Boolean)
          .join(' · ')}
      </p>

      {together.length === 0 ? (
        <StateText>{NO_OVERLAP_NOTE(MIN_FILERS)}</StateText>
      ) : (
        <ol className="mt-5 flex flex-col gap-4">
          {together.map(({ stock, raised }, i) => (
            <li key={stock.ticker}>
              <Link
                to={`/etf/${encodeURIComponent(stock.ticker)}`}
                className="block rounded-2xl border border-slate-200 bg-white px-4 py-4 transition active:scale-[0.99]"
              >
                <div className="flex items-baseline gap-3">
                  <span className="text-primary text-base font-bold tabular-nums">{i + 1}</span>
                  <span className="text-lg font-extrabold text-slate-900">{stock.ticker}</span>
                  <span className="min-w-0 truncate text-base text-slate-500">
                    {stock.issuerName ?? stock.etfStockName}
                  </span>
                  <span className="text-up ml-auto shrink-0 text-[15px] font-bold">
                    {raised.length}명 늘림
                  </span>
                </div>
                <p className="mt-3 text-[15px] text-slate-500">
                  {raised.map((f) => filerPersonName(f.filerKey)).join(' · ')}
                </p>
              </Link>
            </li>
          ))}
        </ol>
      )}
      <Note>{F13_NOTE}</Note>
    </section>
  )
}

// ---------------------------------------------------------------- 액티브 ETF (어제 변화)

const EtfDailyView = () => {
  const { data, isPending, isError } = useEtfDaily()

  if (isPending) return <StateText>불러오는 중…</StateText>
  if (isError)
    return <StateText>ETF 변화를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.</StateText>
  if (data.etfs.length === 0) return <StateText>아직 액티브 ETF 보유 기록이 없어요.</StateText>

  const dates = [...new Set(data.etfs.map((e) => e.snapshotDate))].sort()
  // 시안 22: 함께 늘린 종목 + 가장 많이 늘린 1개 + 가장 많이 줄인 1개
  const top = data.topIncrease[0]
  const bottom = data.topDecrease[0]

  return (
    <section className="mt-6 px-5">
      <h2 className="text-xl font-bold text-slate-900">어제 매니저들이 움직인 종목</h2>
      <p className="mt-1.5 text-sm text-slate-500">
        {data.etfs.map((e) => etfShortName(e.etfCode)).join(' · ')} ·{' '}
        {dates.map(shortDate).join(', ')} 장 마감
      </p>

      <ul className="mt-5 flex flex-col gap-4">
        {data.together.map((t) => (
          <MoveCard
            key={t.rawCode}
            label="두 ETF가 함께 늘렸어요"
            labelClass="text-primary"
            ticker={t.ticker}
          >
            <StockName ticker={t.ticker} name={t.stockName} />
            <span className="text-up ml-auto shrink-0 text-[15px] font-bold tabular-nums">
              {t.moves
                .map((m) => `${etfShortName(m.etfCode)} ${signedPct(m.dayChgPct)}`)
                .join(' · ')}
            </span>
          </MoveCard>
        ))}
        {top && <TopCard label="가장 많이 늘림" move={top} />}
        {bottom && <TopCard label="가장 많이 줄임" move={bottom} />}
      </ul>
      {data.together.length === 0 && !top && !bottom && (
        <StateText>
          어제는 하루 {Math.round(data.threshold * 100)}% 이상 수량을 바꾼 종목이 없어요.
        </StateText>
      )}
      <Note>{ETF_NOTE}</Note>
    </section>
  )
}

const TopCard = ({ label, move }: { label: string; move: EtfMove }) => (
  <MoveCard
    label={`${label} · ${etfShortName(move.etfCode)}`}
    labelClass="text-slate-500"
    ticker={move.ticker}
  >
    <StockName ticker={move.ticker} name={move.stockName} />
    <span
      className={`ml-auto shrink-0 text-lg font-bold tabular-nums ${move.dayChgPct > 0 ? 'text-up' : 'text-down'}`}
    >
      {move.dayChgPct > 0 ? '▲' : '▼'} {signedPct(move.dayChgPct)}
    </span>
  </MoveCard>
)

const MoveCard = ({
  label,
  labelClass,
  ticker,
  children,
}: {
  label: string
  labelClass: string
  ticker: string | null
  children: ReactNode
}) => {
  const body = (
    <>
      <p className={`text-sm font-bold ${labelClass}`}>{label}</p>
      <div className="mt-3 flex items-baseline gap-2">{children}</div>
    </>
  )
  const cls = 'block rounded-2xl border border-slate-200 bg-white px-4 py-4'
  return (
    <li>
      {/* 티커로 바꾸지 못한 종목은 상세로 갈 수 없다 */}
      {ticker ? (
        <Link
          to={`/etf/${encodeURIComponent(ticker)}`}
          className={`${cls} transition active:scale-[0.99]`}
        >
          {body}
        </Link>
      ) : (
        <div className={cls}>{body}</div>
      )}
    </li>
  )
}

const StockName = ({ ticker, name }: { ticker: string | null; name: string | null }) => (
  <span className="flex min-w-0 items-baseline gap-2">
    <span className="text-lg font-extrabold text-slate-900">{ticker ?? name ?? '-'}</span>
    {ticker && name && <span className="truncate text-base text-slate-500">{name}</span>}
  </span>
)

const Note = ({ children }: { children: ReactNode }) => (
  <p className="mt-5 text-center text-[13px] leading-relaxed text-slate-500">{children}</p>
)

const StateText = ({ children }: { children: ReactNode }) => (
  <p className="pt-6 text-sm leading-relaxed text-slate-500">{children}</p>
)
