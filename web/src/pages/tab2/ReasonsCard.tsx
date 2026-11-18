import { useState } from 'react'
import { Link } from 'react-router'
import type { ReasonEvidence, StockReason, StockReasons } from '@/types/overlap'
import { CardLabel, CardTitle } from './CardParts'
import { shortDate } from './labels'
import {
  MY_MAP_BADGE,
  NEW_SKELETON_BADGE,
  NO_REASONS_TEXT,
  reasonsFootNote,
  REJECTED_REASONS_TEXT,
} from './notices'

/**
 * 카드 ② 이유 (AI 추정, 시안 20·24). 이유마다 인과 뼈대를 칸으로 잇고 끝에 보유 변화를 둔다.
 * 파란 칸은 사용자가 배운 개념(learned)이다. 근거는 "근거 · 날짜 제목 외 N건"을 눌러 펼친다.
 * 근거는 제목·날짜·출처·원문 링크만 보여 주고 기사 본문은 보여 주지 않는다 (CLAUDE.md 9).
 */
export const ReasonsCard = ({
  data,
  rejected = false,
}: {
  data: StockReasons | null
  /** 이유를 만들었지만 전부 버려졌으면 "준비 중" 대신 "찾지 못했어요" 고정 문구 (#164) */
  rejected?: boolean
}) => {
  const label = (
    <CardLabel no={2}>
      이유 <span className="font-normal text-slate-500">AI 추정</span>
    </CardLabel>
  )

  if (!data || data.reasons.length === 0) {
    return (
      <>
        {label}
        <CardTitle>왜 움직였을까요?</CardTitle>
        <p className="mt-4 rounded-2xl bg-slate-50 px-4 py-5 text-[15px] leading-relaxed text-slate-500">
          {rejected ? REJECTED_REASONS_TEXT : NO_REASONS_TEXT}
        </p>
      </>
    )
  }

  const end = data.change === 'up' ? '보유 확대' : '보유 축소'

  return (
    <>
      {label}
      <CardTitle>{data.headline}</CardTitle>
      <ul className="mt-4 flex flex-col gap-3">
        {data.reasons.map((r, i) => (
          <li key={`${i}-${r.title}`} className="rounded-2xl bg-slate-50 px-4 py-4">
            <ReasonItem reason={r} index={i + 1} end={end} />
          </li>
        ))}
      </ul>
      <p className="mt-4 text-[13px] leading-relaxed text-slate-500">
        {reasonsFootNote(shortDate(data.bigPeriodEnd))}
      </p>
    </>
  )
}

const ReasonItem = ({
  reason,
  index,
  end,
}: {
  reason: StockReason
  index: number
  end: string
}) => {
  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-[15px] font-bold text-slate-900">
          이유 {index} · 근거 {reason.evidence.length}개
        </h3>
        {reason.inMyMap ? (
          <Link
            to="/mypage/map"
            className="bg-primary/10 text-primary shrink-0 rounded-full px-3 py-1.5 text-[13px] font-bold"
          >
            {MY_MAP_BADGE} ›
          </Link>
        ) : (
          <span className="shrink-0 rounded-full bg-slate-100 px-3 py-1.5 text-[13px] font-bold text-slate-500">
            {NEW_SKELETON_BADGE}
          </span>
        )}
      </div>

      <ol className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-2" aria-label="인과 뼈대">
        {reason.path.map((c) => (
          <li key={c.id} className="flex items-center gap-2">
            <span
              className={`rounded-lg border px-2.5 py-1.5 text-sm font-bold ${
                c.learned
                  ? 'border-primary text-primary bg-blue-50'
                  : 'border-slate-300 bg-white text-slate-800'
              }`}
            >
              {c.name}
            </span>
            <span aria-hidden className="text-slate-400">
              →
            </span>
          </li>
        ))}
        <li>
          <span className="rounded-lg bg-slate-900 px-2.5 py-1.5 text-sm font-bold text-white">
            {end}
          </span>
        </li>
      </ol>

      {reason.evidence.length > 0 && <EvidenceLine evidence={reason.evidence} />}
    </>
  )
}

/** "근거 · 8/14 제목 외 1건" → 누르면 근거 전체(원문 링크) 펼침 */
const EvidenceLine = ({ evidence }: { evidence: ReasonEvidence[] }) => {
  const [open, setOpen] = useState(false)
  const [first] = evidence

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="w-full text-left text-sm leading-relaxed text-slate-500"
      >
        근거 · {shortDate(first.publishedDate)} {first.title}
        {evidence.length > 1 ? ` 외 ${evidence.length - 1}건` : ''}
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5">
          {evidence.map((e) => (
            <li key={e.url} className="text-[13px] leading-relaxed">
              <a
                href={e.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary break-words underline underline-offset-2"
              >
                {e.title}
              </a>
              <span className="block text-slate-400">
                {e.publishedDate}
                {e.issuerName ? ` · ${e.issuerName}` : ''}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
