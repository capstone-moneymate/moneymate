import type { StockNow, StockReasons } from '@/types/overlap'
import { CardLabel, CardTitle } from './CardParts'
import { shortDate, signedPct } from './labels'
import { NO_NOW_TEXT, NOW_LINKED_TITLE } from './notices'

/**
 * 카드 ③ 그래서 지금은? (시안 21·25). 기준일 이후 있었던 일을 사실로만 보여 준다 (docs/modules/stock_now.md).
 * 시안의 큰 제목("기대대로 흘러가는 중")은 판단이라, 코드가 계산한 기준일 이후 주가 변화로 대신한다.
 * 문장(text)은 C 의 stock_now 가 검사를 통과한 것만 오고, 없으면 사실만 보여 준다. 자료 본문은 없다.
 */
export const NowCard = ({ reasons }: { reasons: StockReasons | null }) => {
  const now = reasons?.now ?? null

  return (
    <>
      <CardLabel no={3}>그래서 지금은?</CardLabel>
      {now ? (
        <NowBody now={now} />
      ) : (
        <>
          <CardTitle>기준일 이후{'\n'}있었던 일</CardTitle>
          <p className="mt-4 rounded-2xl bg-slate-50 px-4 py-5 text-[15px] leading-relaxed text-slate-500">
            {NO_NOW_TEXT}
          </p>
        </>
      )}
    </>
  )
}

const NowBody = ({ now }: { now: StockNow }) => {
  const base = shortDate(now.baseDate)
  // returnPct 는 퍼센트 값(12.5 = 12.5%)이라 소수로 바꿔 쓴다
  const title = now.price
    ? `${base} 이후\n주가 ${signedPct(now.price.returnPct / 100, 0)}`
    : `${base} 이후\n있었던 일`

  return (
    <>
      <CardTitle>{title}</CardTitle>
      {now.text && <p className="mt-4 text-[17px] leading-relaxed text-slate-800">{now.text}</p>}

      {now.price && (
        <p className="mt-3 text-sm text-slate-500 tabular-nums">
          {shortDate(now.price.fromDate)} {now.price.fromClose.toLocaleString()} →{' '}
          {shortDate(now.price.toDate)} {now.price.toClose.toLocaleString()}
        </p>
      )}

      {now.laterSources.length > 0 && (
        <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-3.5">
          <p className="text-sm text-slate-500">기준일 뒤 나온 자료</p>
          <ul className="mt-1.5 space-y-1.5">
            {now.laterSources.map((s) => (
              <li key={s.url} className="text-[15px] leading-relaxed">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-800 underline decoration-slate-300 underline-offset-2"
                >
                  {shortDate(s.publishedDate)} {s.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {now.linked.length > 0 && (
        <div className="mt-4 rounded-2xl bg-orange-50 px-4 py-3.5">
          <p className="text-butter-ink text-sm font-bold">{NOW_LINKED_TITLE}</p>
          <ul className="mt-1 space-y-1 text-[15px] leading-relaxed text-slate-800">
            {now.linked.map((l) => (
              <li key={l.conceptId}>
                {l.name} · 이유 「{l.reasonTitle}」
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}
