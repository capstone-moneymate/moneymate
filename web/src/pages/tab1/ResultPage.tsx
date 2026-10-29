import { Link, useParams } from 'react-router'
import { useCard } from '@/api/cards'
import { useLearnStore } from '@/store/learnStore'
import type { CardDetail, Step } from '@/types/card'
import { CloseLink } from '@/pages/tab1/CloseLink'
import { AiAnalysis } from '@/pages/tab1/steps/AiAnalysis'

/** 결과 화면: 종합 점수, 개념 이해도, 적용 판단, 학습 요약 → 13F·ETF로 (유형 3은 종목 상세로) */
export const ResultPage = () => {
  const { cardId = '' } = useParams()
  const { data: card } = useCard(cardId)
  const results = useLearnStore((s) => s.results[cardId])

  if (!card) return <p className="p-5 text-sm text-slate-500">불러오는 중…</p>
  if (!results) {
    return (
      <div className="p-5 text-sm text-slate-500">
        학습 기록이 없어요. (새로고침하면 기록이 사라져요)
        <Link to={`/news/${card.id}/learn`} className="text-primary mt-3 block font-semibold">
          처음부터 다시 풀기 ›
        </Link>
      </div>
    )
  }

  const values = Object.values(results)
  const coded = values.filter((r) => r.isCorrect !== null)
  const concept = coded.length
    ? Math.round((coded.filter((r) => r.isCorrect).length / coded.length) * 100)
    : null
  const grade = values.find((r) => r.grade)?.grade
  const judgement = grade?.score ?? null
  const parts = [concept, judgement].filter((v): v is number => v !== null)
  const total = parts.length ? Math.round(parts.reduce((a, b) => a + b, 0) / parts.length) : 0
  const hasAiStep = card.steps.some((s) => s.kind === 'ai_analysis')

  return (
    <div className="flex min-h-full flex-col px-5 pt-5 pb-5">
      <div className="flex items-center justify-between">
        <p className="text-primary text-sm font-semibold">학습 완료</p>
        <CloseLink />
      </div>
      <h2 className="mt-2 text-xl leading-snug font-bold text-slate-900">{card.title}</h2>

      <div className="mt-5 rounded-2xl bg-slate-50 px-4 py-5 text-center">
        <p className="text-sm text-slate-500">종합 점수</p>
        <p className="text-primary mt-1 text-4xl font-bold tabular-nums">{total}</p>
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-2">
        <Score label="개념 이해도" value={concept} />
        <Score label="적용 판단" value={judgement} />
      </dl>

      <section className="mt-5">
        <h3 className="font-bold text-slate-900">학습 요약</h3>
        <ul className="mt-2 flex flex-col gap-1 text-sm text-slate-700">
          {summaryLines(card).map((line) => (
            <li key={line}>· {line}</li>
          ))}
        </ul>
      </section>

      {/* 유형 3은 AI 분석 단계에서 이미 봤으므로 다시 보여 주지 않는다 */}
      {grade && !hasAiStep && (
        <div className="mt-5">
          <AiAnalysis grade={grade} />
        </div>
      )}

      <div className="mt-auto flex flex-col gap-2 pt-6">
        {card.type === 3 && card.ticker ? (
          <Link
            to={`/etf?ticker=${card.ticker}`}
            className="bg-primary rounded-2xl py-4 text-center font-bold text-white"
          >
            {card.ticker} 종목 상세로 이어 보기 ›
          </Link>
        ) : (
          <Link to="/etf" className="bg-primary rounded-2xl py-4 text-center font-bold text-white">
            13F·ETF에서 이어 보기 ›
          </Link>
        )}
        <Link
          to="/"
          className="rounded-2xl bg-slate-100 py-4 text-center font-semibold text-slate-700"
        >
          뉴스 홈으로
        </Link>
      </div>
    </div>
  )
}

const Score = ({ label, value }: { label: string; value: number | null }) => {
  return (
    <div className="rounded-2xl bg-slate-50 px-4 py-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-lg font-bold text-slate-900 tabular-nums">{value ?? '-'}</dd>
    </div>
  )
}

/** 배운 용어와 인과 뼈대 */
const summaryLines = (card: CardDetail) => {
  const lines: string[] = []
  const terms = card.steps.flatMap((s: Step) =>
    s.kind === 'concept' ? s.terms.map((t) => t.term) : [],
  )
  if (terms.length) lines.push(`배운 개념: ${terms.join(', ')}`)
  for (const s of card.steps) {
    if (s.kind === 'causal_order') {
      const labels = s.conceptIds.map((id) => s.items.find((i) => i.conceptId === id)?.label ?? id)
      lines.push(`인과 뼈대: ${labels.join(' → ')}`)
    }
  }
  return lines
}
