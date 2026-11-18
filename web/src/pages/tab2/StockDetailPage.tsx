import { useState, type ReactNode } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router'
import { StockNotFoundError, useStockOverlap } from '@/api/overlap'
import type { EtfChange, FilerChange, StockOverlap } from '@/types/overlap'
import { CardLabel, CardTitle, Rate } from './CardParts'
import { etfShortName, FILERS, filerPersonName, isBigUp, quarterMonths, shortDate } from './labels'
import { NowCard } from './NowCard'
import { AGAINST_TREND_TEXT, AGAINST_TREND_TITLE, DETAIL_NOTE } from './notices'
import { ReasonsCard } from './ReasonsCard'

const CARD_COUNT = 3

/**
 * 탭2 종목 상세 (시안 19~25): 위 막대 3개 → 종목 헤더 → 카드 ① 무엇이 바뀌었나 / ② 이유 / ③ 지금은.
 * "다음 카드"로 한 장씩 넘기고 마지막 장에서 "목록으로".
 * 시안의 섹터·성격 태그와 회사 소개 한 줄은 저장된 데이터가 없어 비워 둔다 (docs/modules/tab2_screens.md).
 */
export const StockDetailPage = () => {
  const { ticker = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { data, isPending, isError, error } = useStockOverlap(ticker)
  const [index, setIndex] = useState(0)
  // 탭2 안에서 왔으면 이전 화면(스위치 상태 유지), 주소로 바로 들어왔으면 탭2 메인
  const close = () => (location.key === 'default' ? navigate('/etf') : navigate(-1))
  const last = index === CARD_COUNT - 1

  return (
    <div className="flex min-h-full flex-col px-6 pt-6 pb-4">
      <div className="flex gap-1.5" aria-label={`카드 ${index + 1} / ${CARD_COUNT}`}>
        {Array.from({ length: CARD_COUNT }, (_, i) => (
          <span
            key={i}
            className={`h-[3px] flex-1 rounded-full ${i <= index ? 'bg-primary' : 'bg-blue-100'}`}
          />
        ))}
      </div>

      <header className="mt-6 flex items-start justify-between gap-3">
        <h1 className="flex min-w-0 items-baseline gap-2.5">
          <span className="text-[34px] leading-none font-extrabold text-slate-900">
            {ticker.toUpperCase()}
          </span>
          {data && (
            <span className="truncate text-lg text-slate-500">
              {data.issuerName ?? data.etfStockName}
            </span>
          )}
        </h1>
        <button
          type="button"
          onClick={close}
          aria-label="닫기"
          className="flex size-11 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-700"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            aria-hidden
          >
            <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
          </svg>
        </button>
      </header>
      <hr className="mt-5 border-slate-200" />

      <div className="flex flex-1 flex-col justify-center py-6">
        {isPending ? (
          <StateText>불러오는 중…</StateText>
        ) : isError ? (
          <StateText>
            {error instanceof StockNotFoundError
              ? `${ticker.toUpperCase()} 종목은 지금 큰손과 액티브 ETF가 겹친 종목이 아니에요.`
              : '종목 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'}
          </StateText>
        ) : index === 0 ? (
          <ChangedCard stock={data} />
        ) : index === 1 ? (
          <ReasonsCard data={data.reasons} rejected={data.reasonsRejected} />
        ) : (
          <NowCard reasons={data.reasons} />
        )}
      </div>

      <button
        type="button"
        onClick={() => (last || isError ? close() : setIndex(index + 1))}
        className="bg-primary h-[52px] w-full shrink-0 rounded-2xl text-[17px] font-bold text-white"
      >
        {last || isError ? '목록으로' : '다음 카드 ›'}
      </button>
      <p className="mt-3 text-center text-xs leading-relaxed text-slate-500">{DETAIL_NOTE}</p>
    </div>
  )
}

// ---------------------------------------------------------------- 카드 ① 무엇이 바뀌었나

/** ETF 가 분기 말 이후 늘렸는지 (새로 담았으면 trendChgPct 가 null) */
const etfUp = (e: EtfChange) => e.trendChgPct === null || e.trendChgPct > 0

/** 큰 제목: 늘린 큰손 수와 계속 늘린 ETF 수를 코드가 센다 */
const headline = (stock: StockOverlap) => {
  const n = stock.filers.filter(isBigUp).length
  const m = stock.etfs.filter(etfUp).length
  const dayUp = stock.etfs.filter((e) => e.dayChgPct !== null && e.dayChgPct > 0).length
  if (n > 0 && m > 0) return `큰손 ${n}명이 늘리고,\nETF ${m}곳도 계속 사는 중`
  if (n > 0) return `큰손 ${n}명이 늘렸어요`
  if (dayUp >= 2 && dayUp === stock.etfs.length) return '두 ETF가 어제\n함께 늘렸어요'
  if (m > 0) return `ETF ${m}곳이\n계속 늘리는 중`
  return '큰손과 ETF의\n최근 기록이에요'
}

const FilerValue = ({ f }: { f: FilerChange }) => {
  switch (f.changeType) {
    case 'new':
      return <Rate value={1} text="신규" />
    case 'exit':
      return <Rate value={-1} text="모두 정리" />
    case 'unchanged':
      return <span className="text-slate-500">변화 없음</span>
    default:
      return f.chgPct === null ? (
        <span className="text-slate-400">-</span>
      ) : (
        <Rate value={f.chgPct} />
      )
  }
}

const Row = ({ name, children }: { name: string; children: ReactNode }) => (
  <li className="flex items-center justify-between py-1.5 text-[17px]">
    <span className="text-slate-800">{name}</span>
    {children}
  </li>
)

const ChangedCard = ({ stock }: { stock: StockOverlap }) => {
  const order = FILERS.map((f) => f.key as string)
  const filers = stock.filers
    .filter((f) => f.changeType !== null)
    .sort((a, b) => order.indexOf(a.filerKey) - order.indexOf(b.filerKey))
  const periodEnd = stock.filers[0]?.periodEnd
  const days = stock.etfs.filter((e) => e.dayChgPct !== null)
  // 분기 말 이후 추세와 어제 방향이 반대인 ETF (어제 0% 는 반대로 보지 않는다)
  const against = days.filter((e) => e.dayChgPct !== 0 && etfUp(e) !== (e.dayChgPct as number) > 0)

  return (
    <>
      <CardLabel no={1}>무엇이 바뀌었나요?</CardLabel>
      <CardTitle>{headline(stock)}</CardTitle>

      <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-4">
        {filers.length > 0 && (
          <>
            <p className="text-sm text-slate-500">
              큰손{periodEnd ? ` · ${quarterMonths(periodEnd)}` : ''}
            </p>
            <ul className="mt-1">
              {filers.map((f) => (
                <Row key={f.filerKey} name={filerPersonName(f.filerKey)}>
                  <FilerValue f={f} />
                </Row>
              ))}
            </ul>
          </>
        )}
        {stock.etfs.length > 0 && (
          <>
            <p className={`text-sm text-slate-500 ${filers.length > 0 ? 'mt-3' : ''}`}>
              액티브 ETF{periodEnd ? ` · ${shortDate(periodEnd)} 이후` : ''}
            </p>
            <ul className="mt-1">
              {stock.etfs.map((e) => (
                <Row key={e.etfCode} name={etfShortName(e.etfCode)}>
                  {e.trendChgPct === null ? (
                    <Rate value={1} text="신규" />
                  ) : (
                    <Rate value={e.trendChgPct} />
                  )}
                </Row>
              ))}
            </ul>
          </>
        )}
      </div>

      {days.length > 0 && (
        <div className="mt-3 rounded-2xl border border-dashed border-slate-300 px-4 py-3.5">
          <div className="flex items-center justify-between gap-2">
            <span className="shrink-0 text-sm text-slate-500">어제만 보면</span>
            <span className="flex gap-3 text-[15px]">
              {days.map((e) => (
                <span key={e.etfCode} className="whitespace-nowrap">
                  <span className="mr-1 text-slate-600">{etfShortName(e.etfCode)}</span>
                  <Rate value={e.dayChgPct as number} digits={1} />
                </span>
              ))}
            </span>
          </div>
          {against.length > 0 && (
            <div className="mt-3 border-t border-slate-200 pt-3">
              <p className="text-sm font-bold text-amber-700">{AGAINST_TREND_TITLE}</p>
              <p className="mt-1 text-[15px] leading-relaxed text-slate-700">
                {against.map((e) => etfShortName(e.etfCode)).join('·')} · {AGAINST_TREND_TEXT}
              </p>
            </div>
          )}
        </div>
      )}
    </>
  )
}

const StateText = ({ children }: { children: ReactNode }) => (
  <p className="text-sm leading-relaxed text-slate-500">{children}</p>
)
