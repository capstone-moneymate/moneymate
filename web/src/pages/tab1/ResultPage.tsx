import { Link, useNavigate, useParams } from 'react-router'
import { useCard } from '@/api/cards'
import { SHOW_TAB2 } from '@/components/BottomNav'
import { reviewLabel, useReviewDate, withReview } from '@/lib/review'
import { useLearnStore } from '@/store/learnStore'
import type { AnswerResult, CardDetail } from '@/types/card'
import { BackButton, CloseLink } from '@/pages/tab1/CloseLink'
import { AiAnalysis } from '@/pages/tab1/steps/AiAnalysis'

/**
 * 결과 화면 (UI 시안 17): 종합 점수 원, 개념 이해도·적용 판단, 오늘의 학습 요약, AI 피드백
 * → 13F·ETF로 (유형 3은 종목 상세로)
 */
export const ResultPage = () => {
  const { cardId = '' } = useParams()
  const navigate = useNavigate()
  const { data: card } = useCard(cardId)
  const results = useLearnStore((s) => s.results[cardId])
  const review = useReviewDate()

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
  // 채점된 단계가 하나도 없으면(판단 채점 실패·한도 초과뿐인 유형 3 등) 점수 대신 '-'
  const total = parts.length ? Math.round(parts.reduce((a, b) => a + b, 0) / parts.length) : null

  return (
    <div className="flex min-h-full flex-col px-5 pt-4 pb-5">
      <div className="flex items-center justify-between">
        <BackButton
          label="카드뉴스 다시 보기"
          onClick={() => navigate(withReview(`/news/${card.id}`, review))}
        />
        <CloseLink />
      </div>
      <h2 className="mt-5 text-2xl leading-snug font-bold text-slate-900">
        {review ? (
          <>
            {reviewLabel(review)}의 판단,
            <br />
            다시 봤어요
          </>
        ) : (
          <>
            오늘의 판단,
            <br />
            기록했어요
          </>
        )}
      </h2>

      <ScoreRing value={total} />

      <dl className="mt-6 grid grid-cols-2 gap-2.5">
        <Score label="개념 이해도" value={concept} />
        <Score label="적용 판단" value={judgement} />
      </dl>

      <section className="mt-7">
        <h3 className="font-bold text-slate-900">오늘의 학습 요약</h3>
        <ul className="mt-3 flex flex-col gap-2">
          {summaryLines(card, results).map((line) => (
            <li
              key={line}
              className="flex items-center gap-3 rounded-2xl bg-slate-100 px-4 py-3.5 text-sm font-semibold text-slate-900"
            >
              <CheckIcon />
              {line}
            </li>
          ))}
        </ul>
      </section>

      {/* AI 피드백: 판단해보기 채점 결과 (모든 유형 공통) */}
      {grade && (
        <div className="mt-6">
          <AiAnalysis grade={grade} />
        </div>
      )}

      <div className="mt-auto flex flex-col items-center gap-2 pt-7">
        {review ? (
          <Link
            to="/mypage"
            className="bg-primary w-full rounded-2xl py-4 text-center font-bold text-white"
          >
            학습 달력으로
          </Link>
        ) : !SHOW_TAB2 ? (
          // 탭2를 숨긴 동안에는 홈으로 돌아가는 버튼 하나만 둔다
          <Link
            to="/"
            className="bg-primary w-full rounded-2xl py-4 text-center font-bold text-white"
          >
            홈으로
          </Link>
        ) : card.type === 3 && card.ticker ? (
          <Link
            to={`/etf?ticker=${card.ticker}`}
            className="bg-primary w-full rounded-2xl py-4 text-center font-bold text-white"
          >
            {card.ticker} 종목 상세로 이어 보기 ›
          </Link>
        ) : (
          <Link
            to="/etf"
            className="bg-primary w-full rounded-2xl py-4 text-center font-bold text-white"
          >
            13F·ETF로 실제 행동 복습하기 ›
          </Link>
        )}
        {SHOW_TAB2 && (
          <Link to="/" className="min-h-11 px-4 py-3 text-slate-500">
            홈으로
          </Link>
        )}
      </div>
    </div>
  )
}

/** 종합 점수 원 (100점이면 한 바퀴) */
const ScoreRing = ({ value }: { value: number | null }) => {
  const r = 54
  const len = 2 * Math.PI * r
  const ratio = value === null ? 0 : Math.min(Math.max(value, 0), 100) / 100

  return (
    <div className="relative mx-auto mt-6 size-36">
      <svg viewBox="0 0 128 128" className="size-full -rotate-90" aria-hidden>
        <circle cx="64" cy="64" r={r} fill="none" stroke="#e2e8f0" strokeWidth="12" />
        <circle
          cx="64"
          cy="64"
          r={r}
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${len * ratio} ${len}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-4xl font-bold text-slate-900 tabular-nums">{value ?? '-'}</p>
        <p className="mt-0.5 text-xs text-slate-500">종합 점수</p>
      </div>
    </div>
  )
}

const Score = ({ label, value }: { label: string; value: number | null }) => {
  return (
    <div className="rounded-2xl bg-slate-100 px-4 py-4 text-center">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="mt-1 text-2xl font-bold text-slate-900 tabular-nums">
        {value === null ? '-' : `${value}점`}
      </dd>
    </div>
  )
}

/** 오늘 한 단계들을 한 줄씩 (카드 → 개념 → 퀴즈 → 인과 → 차트 → 판단) */
const summaryLines = (card: CardDetail, results: Record<string, AnswerResult>) => {
  const lines = [`오늘의 뉴스 확인 · ${card.title}`]
  const terms = card.steps.flatMap((s) => (s.kind === 'concept' ? s.terms.map((t) => t.term) : []))
  if (terms.length) lines.push(`개념 학습 완료 · ${terms.join(', ')}`)

  const quizzes = card.steps.filter((s) => s.kind === 'quiz')
  if (quizzes.length) {
    const right = quizzes.filter((s) => results[s.id]?.isCorrect).length
    lines.push(`간단 퀴즈 · ${quizzes.length}문제 중 ${right}개 정답`)
  }
  for (const s of card.steps) {
    if (s.kind === 'causal_order') {
      const labels = s.conceptIds.map((id) => s.items.find((i) => i.conceptId === id)?.label ?? id)
      lines.push(`인과관계 · ${labels.join(' → ')}`)
    }
    if (s.kind === 'chart')
      lines.push(`차트 읽기 · ${results[s.id]?.isCorrect ? '정답' : '해설 확인'}`)
    // 풀었던 내용 보기에서 그날 판단해보기를 안 냈으면 결과가 없다
    if (s.kind === 'judgement')
      lines.push(results[s.id] ? '판단 시뮬레이션 완료' : '판단 시뮬레이션 · 풀지 않음')
  }
  return lines
}

function CheckIcon() {
  return (
    <span className="bg-primary flex size-6 shrink-0 items-center justify-center rounded-md text-white">
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        aria-hidden
      >
        <path d="M5 12l5 5 9-10" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  )
}
