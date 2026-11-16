import { ChangeRate } from '@/components/ChangeRate'
import type { StockNow } from '@/types/overlap'
import { formatDate } from './labels'
import { NO_NOW_TEXT, NOW_NOTE } from './notices'

/**
 * 카드 ③ 지금은. 기준일 이후 주가·자료·오늘 배운 개념 연결을 사실로만 보여 준다 (docs/modules/stock_now.md).
 * 문장(text)이 없으면 사실만 보여 준다. 자료는 제목·날짜·원문 링크만, 본문은 없다.
 */
export const NowCard = ({ now }: { now: StockNow | null }) => {
  return (
    <section className="mx-5 mt-3 rounded-2xl border border-slate-200 p-4 shadow-sm">
      <p className="text-primary text-xs font-bold">카드 ③</p>
      <h2 className="mt-0.5 text-lg font-bold text-slate-900">지금은</h2>
      {now ? (
        <NowBody now={now} />
      ) : (
        <p className="mt-2 text-sm leading-relaxed text-slate-500">{NO_NOW_TEXT}</p>
      )}
    </section>
  )
}

const NowBody = ({ now }: { now: StockNow }) => {
  return (
    <>
      <p className="mt-1 text-xs text-slate-400">{formatDate(now.baseDate)} 기준일 이후</p>

      {now.text && <p className="mt-3 text-sm leading-relaxed text-slate-700">{now.text}</p>}

      {now.price && (
        <div className="mt-3 rounded-xl bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-slate-700">주가</h3>
          <p className="mt-1 flex items-center justify-between text-sm">
            <span className="text-slate-600 tabular-nums">
              {formatDate(now.price.fromDate)} {now.price.fromClose.toLocaleString()} →{' '}
              {formatDate(now.price.toDate)} {now.price.toClose.toLocaleString()}
            </span>
            {/* returnPct 는 퍼센트 값이라 ChangeRate(소수)에 맞춰 100 으로 나눈다 */}
            <ChangeRate value={now.price.returnPct / 100} className="tabular-nums" />
          </p>
        </div>
      )}

      {now.laterSources.length > 0 && (
        <>
          <h3 className="mt-3 text-sm font-semibold text-slate-700">기준일 뒤 나온 자료</h3>
          <ul className="mt-1 space-y-2">
            {now.laterSources.map((s) => (
              <li key={s.url} className="text-xs leading-relaxed">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary break-words underline underline-offset-2"
                >
                  {s.title}
                </a>
                <span className="block text-slate-400">{s.publishedDate}</span>
                {Object.keys(s.numbers).length > 0 && (
                  <ul className="mt-1 flex flex-wrap gap-1">
                    {Object.entries(s.numbers).map(([k, v]) => (
                      <li key={k} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
                        {k} {typeof v === 'number' ? v.toLocaleString() : v}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      {now.linked.length > 0 && (
        <>
          <h3 className="mt-3 text-sm font-semibold text-slate-700">오늘 배운 뉴스와 연결</h3>
          <ul className="mt-1 space-y-1 text-sm text-slate-700">
            {now.linked.map((l) => (
              <li key={l.conceptId}>
                <span className="text-primary font-semibold">{l.name}</span> → 이유 「
                {l.reasonTitle}」
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="mt-3 text-xs leading-relaxed text-slate-500">{NOW_NOTE}</p>
    </>
  )
}
