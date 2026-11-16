import { useLocation, useNavigate, useParams } from 'react-router'
import { StockNotFoundError, useStockOverlap } from '@/api/overlap'
import { ChangeRate } from '@/components/ChangeRate'
import type { StockOverlap } from '@/types/overlap'
import { DirectionChip } from './DirectionChip'
import { FilerChangeText, TrendText } from './FilerChangeText'
import {
  DIFF_NOTE,
  etfFullName,
  etfShortName,
  FILERS,
  filerShortName,
  formatDate,
  GUIDE_NOTE,
} from './labels'

/** 탭2 종목 상세: 종목 헤더 → 카드 ① 무엇이 바뀌었나 → 카드 ②③ 자리 (#101) */
export const StockDetailPage = () => {
  const { ticker = '' } = useParams()
  const { data, isPending, isError, error } = useStockOverlap(ticker)

  return (
    <div className="pb-6">
      <TopBar />
      {isPending ? (
        <StateText>불러오는 중…</StateText>
      ) : isError ? (
        <StateText>
          {error instanceof StockNotFoundError
            ? `${ticker.toUpperCase()} 종목은 지금 큰손과 액티브 ETF가 겹친 종목이 아니에요.`
            : '종목 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'}
        </StateText>
      ) : (
        <StockBody stock={data} />
      )}
    </div>
  )
}

/** 뒤로: 탭2 안에서 왔으면 이전 화면(스위치 상태 유지), 주소로 바로 들어왔으면 탭2 메인 */
const TopBar = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const goBack = () => (location.key === 'default' ? navigate('/etf') : navigate(-1))

  return (
    <div className="flex items-center px-3 pt-3">
      <button
        type="button"
        onClick={goBack}
        aria-label="뒤로"
        className="flex size-11 items-center justify-center rounded-full text-slate-700 active:bg-slate-100"
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden
        >
          <path d="M15 5l-7 7 7 7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </div>
  )
}

const StockBody = ({ stock }: { stock: StockOverlap }) => {
  const byFiler = new Map(stock.filers.map((f) => [f.filerKey, f]))
  const periodEnd = stock.filers[0]?.periodEnd
  const snapshotDate = stock.etfs[0]?.snapshotDate
  const hasDiff = stock.pairs.some((p) => p.direction === 'diff')

  return (
    <>
      {/* 종목 헤더: 섹터·성격 태그와 회사 소개는 데이터가 없어 비워 둔다 */}
      <header className="px-5 pt-1">
        <h1 className="text-2xl font-bold text-slate-900">{stock.ticker}</h1>
        <p className="mt-0.5 text-sm text-slate-500">{stock.issuerName ?? stock.etfStockName}</p>
      </header>

      <section className="mx-5 mt-5 rounded-2xl border border-slate-200 p-4 shadow-sm">
        <p className="text-primary text-xs font-bold">카드 ①</p>
        <h2 className="mt-0.5 text-lg font-bold text-slate-900">무엇이 바뀌었나</h2>

        <h3 className="mt-4 text-sm font-semibold text-slate-700">큰손 13F</h3>
        <p className="text-xs text-slate-400">
          {periodEnd ? `${formatDate(periodEnd)} 분기 말 기록, 직전 분기 대비` : '분기 말 기록'}
        </p>
        <ul className="mt-2 divide-y divide-slate-100">
          {FILERS.map((f) => (
            <li key={f.key} className="flex min-h-12 items-center justify-between gap-2 py-2">
              <span className="min-w-0">
                <span className="block text-sm font-medium text-slate-900">{f.name}</span>
                <span className="block text-xs text-slate-400">{f.person}</span>
              </span>
              <FilerChangeText change={byFiler.get(f.key)} />
            </li>
          ))}
        </ul>

        <h3 className="mt-4 text-sm font-semibold text-slate-700">액티브 ETF 추세</h3>
        <p className="text-xs text-slate-400">
          13F 분기 말 이후{snapshotDate ? ` ~ ${formatDate(snapshotDate)}` : ''}
        </p>
        <ul className="mt-2 divide-y divide-slate-100">
          {stock.etfs.map((e) => (
            <li key={e.etfCode} className="flex min-h-12 items-center justify-between gap-2 py-2">
              <span className="text-sm font-medium text-slate-900">{etfFullName(e.etfCode)}</span>
              <TrendText value={e.trendChgPct} />
            </li>
          ))}
        </ul>

        <div className="mt-4 rounded-xl bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-slate-700">어제만 보면</h3>
          <ul className="mt-1">
            {stock.etfs.map((e) => (
              <li key={e.etfCode} className="flex items-center justify-between py-1 text-sm">
                <span className="text-slate-600">{etfShortName(e.etfCode)}</span>
                {e.dayChgPct === null ? (
                  <span className="text-slate-400">-</span>
                ) : (
                  <ChangeRate value={e.dayChgPct} className="tabular-nums" />
                )}
              </li>
            ))}
          </ul>
        </div>

        <h3 className="mt-4 text-sm font-semibold text-slate-700">방향 비교</h3>
        <ul className="mt-1">
          {stock.pairs.map((p) => (
            <li
              key={`${p.filerKey}-${p.etfCode}`}
              className="flex items-center justify-between py-1.5"
            >
              <span className="text-sm text-slate-600">
                {filerShortName(p.filerKey)} × {etfShortName(p.etfCode)}
              </span>
              <DirectionChip direction={p.direction} />
            </li>
          ))}
        </ul>
        {hasDiff && <p className="mt-2 text-xs leading-relaxed text-slate-500">{DIFF_NOTE}</p>}
      </section>

      {/* 카드 ②③ 은 #101 에서 만든다 */}
      <Placeholder label="카드 ②" title="이유 (AI 추정)" />
      <Placeholder label="카드 ③" title="지금은" />

      <p className="mx-5 mt-6 rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-500">
        {GUIDE_NOTE}
      </p>
    </>
  )
}

const Placeholder = ({ label, title }: { label: string; title: string }) => {
  return (
    <section className="mx-5 mt-3 rounded-2xl border border-dashed border-slate-300 p-4">
      <p className="text-xs font-bold text-slate-400">{label}</p>
      <h2 className="mt-0.5 font-bold text-slate-400">{title}</h2>
      <p className="mt-1 text-sm text-slate-400">준비 중</p>
    </section>
  )
}

const StateText = ({ children }: { children: React.ReactNode }) => {
  return <p className="px-5 pt-4 text-sm leading-relaxed text-slate-500">{children}</p>
}
