import type { ReasonEvidence, StockReason, StockReasons } from '@/types/overlap'
import { evidenceKey, evidenceNumbers } from './evidenceNumbers'
import { formatDate } from './labels'
import { MY_MAP_BADGE, NO_REASONS_TEXT, REASONS_AI_NOTE } from './notices'

/**
 * 카드 ② 이유 (AI 추정). 이유는 가로로 넘겨 본다 (서비스흐름 "이유는 카드로 짧게").
 * 근거 번호는 종목 안에서 처음 나온 순서대로 1부터 다시 매긴다. 같은 자료는 같은 번호다.
 * 근거는 제목·날짜·출처·원문 링크만 보여 주고 기사 본문은 보여 주지 않는다 (CLAUDE.md 9).
 */
export const ReasonsCard = ({ data }: { data: StockReasons | null }) => {
  if (!data || data.reasons.length === 0) {
    return (
      <CardFrame title="이유">
        <p className="mt-2 text-sm leading-relaxed text-slate-500">{NO_REASONS_TEXT}</p>
      </CardFrame>
    )
  }

  const numbers = evidenceNumbers(data.reasons)

  return (
    <CardFrame title={data.headline}>
      <p className="mt-1 text-xs text-slate-400">
        {formatDate(data.bigPeriodEnd)} 분기 말 기록 기준
      </p>
      <ul
        className="-mx-4 mt-3 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-2"
        aria-label="이유 목록 (옆으로 넘겨 보기)"
      >
        {data.reasons.map((r, i) => (
          <li
            key={`${i}-${r.title}`}
            className="w-[85%] shrink-0 snap-center rounded-xl bg-slate-50 p-3.5"
          >
            <ReasonItem reason={r} index={i + 1} total={data.reasons.length} numbers={numbers} />
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs leading-relaxed text-slate-500">{REASONS_AI_NOTE}</p>
    </CardFrame>
  )
}

const ReasonItem = ({
  reason,
  index,
  total,
  numbers,
}: {
  reason: StockReason
  index: number
  total: number
  numbers: Map<string, number>
}) => {
  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-slate-400 tabular-nums">
          {index} / {total}
        </span>
        {reason.inMyMap && <MyMapBadge />}
      </div>
      <h3 className="mt-1 font-bold text-slate-900">{reason.title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-slate-700">{reason.body}</p>

      <p className="mt-3 text-xs font-semibold text-slate-500">인과 뼈대</p>
      <ol className="mt-1 flex flex-wrap items-center gap-1 text-xs">
        {reason.path.map((c, i) => (
          <li key={c.id} className="flex items-center gap-1">
            {i > 0 && (
              <span aria-hidden className="text-slate-400">
                →
              </span>
            )}
            <span
              className={`rounded-full px-2 py-0.5 ${
                c.learned ? 'bg-primary/10 text-primary font-semibold' : 'bg-white text-slate-700'
              }`}
            >
              {c.name}
            </span>
          </li>
        ))}
        <li>
          <ForceText direction={reason.direction} />
        </li>
      </ol>

      {reason.evidence.length > 0 && (
        <>
          <p className="mt-3 text-xs font-semibold text-slate-500">근거 자료</p>
          <ul className="mt-1 space-y-1.5">
            {reason.evidence.map((e) => (
              <EvidenceLine key={evidenceKey(e)} evidence={e} no={numbers.get(evidenceKey(e))} />
            ))}
          </ul>
        </>
      )}
    </>
  )
}

/** 시작 개념이 커질 때 끝 개념이 받는 힘 */
const ForceText = ({ direction }: { direction: 'up' | 'down' }) => {
  return direction === 'up' ? (
    <span className="text-up font-semibold">▲ 올리는 힘</span>
  ) : (
    <span className="text-down font-semibold">▼ 누르는 힘</span>
  )
}

const EvidenceLine = ({ evidence, no }: { evidence: ReasonEvidence; no?: number }) => {
  return (
    <li className="flex gap-1.5 text-xs leading-relaxed">
      <span className="shrink-0 font-semibold text-slate-500 tabular-nums">[{no}]</span>
      <span className="min-w-0">
        <a
          href={evidence.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary break-words underline underline-offset-2"
        >
          {evidence.title}
        </a>
        <span className="block text-slate-400">
          {evidence.publishedDate}
          {evidence.issuerName ? ` · ${evidence.issuerName}` : ''}
        </span>
      </span>
    </li>
  )
}

export const MyMapBadge = () => {
  return (
    <span className="bg-primary/10 text-primary inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold">
      {MY_MAP_BADGE}
    </span>
  )
}

const CardFrame = ({ title, children }: { title: string; children: React.ReactNode }) => {
  return (
    <section className="mx-5 mt-3 rounded-2xl border border-slate-200 p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <p className="text-primary text-xs font-bold">카드 ②</p>
        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
          AI 추정
        </span>
      </div>
      <h2 className="mt-0.5 text-lg font-bold text-slate-900">{title}</h2>
      {children}
    </section>
  )
}
