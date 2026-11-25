import { Link, useNavigate, useParams } from 'react-router'
import { useCard } from '@/api/cards'
import { useGhost } from '@/api/ghost'
import { SHOW_TAB2 } from '@/components/BottomNav'
import { Mate } from '@/components/Mate'
import { reviewLabel, useReviewDate, withReview } from '@/lib/review'
import { useLearnStore } from '@/store/learnStore'
import type { AnswerResult, CardDetail } from '@/types/card'
import { Cheer } from '@/pages/tab1/Cheer'
import { LessonTop } from '@/pages/tab1/LessonTop'
import { GhostCard } from '@/pages/tab1/GhostCard'
import { AiAnalysis } from '@/pages/tab1/steps/AiAnalysis'
import { VerdictIcon } from '@/pages/tab1/steps/AnswerFeedback'

/**
 * 결과 화면 (UI 시안 app.html 의 완료 화면): 마스코트와 완료 문구, 점수 세 칸(종합·개념 이해도·적용 판단),
 * 오늘 한 것, 지난번과 비교, AI 피드백. 방금 다 풀고 들어오면 '잘했어요!' 축하 화면이 잠깐 덮는다
 * → 13F·ETF로 (유형 3은 종목 상세로)
 * 이 카드를 이전에 끝까지 푼 적이 있으면 지난번과 이번을 나란히 보여 준다 (고스트 비교, 추가 구현 2-6)
 */
export const ResultPage = () => {
  const { cardId = '' } = useParams()
  const navigate = useNavigate()
  const { data: card } = useCard(cardId)
  const results = useLearnStore((s) => s.results[cardId])
  const review = useReviewDate()
  // 풀었던 내용 보기는 새로 푼 게 아니라서 비교하지 않는다. 방금 푼 기록이 없으면(새로고침) 부르지 않는다
  const ghost = useGhost(cardId, 'result', !review && !!results)

  if (!card) return <p className="text-sub p-5 text-sm font-semibold">불러오는 중…</p>
  if (!results) {
    return (
      <div className="mm-empty">
        <Mate mood="think" />
        <p>
          학습 기록이 없어요.
          <br />
          (새로고침하면 기록이 사라져요)
        </p>
        <Link to={`/news/${card.id}/learn`} className="mm-btn">
          처음부터 다시 풀기
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

  const primary = review
    ? { to: '/mypage', label: '학습 달력으로' }
    : !SHOW_TAB2
      ? // 탭2를 숨긴 동안에는 홈으로 돌아가는 버튼 하나만 둔다
        { to: '/', label: '홈으로' }
      : card.type === 3 && card.ticker
        ? { to: `/etf?ticker=${card.ticker}`, label: `${card.ticker} 종목 상세로 이어 보기` }
        : { to: '/etf', label: '13F·ETF로 실제 행동 복습하기' }

  return (
    <div className="relative flex h-full flex-col overflow-hidden">
      {!review && <Cheer />}
      <LessonTop
        progress={100}
        onBack={() => navigate(withReview(`/news/${card.id}`, review))}
        backLabel="카드뉴스 다시 보기"
      />

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mm-l-body">
          <div className="mm-done-top">
            <Mate mood="happy" />
            <h2>{review ? `${reviewLabel(review)}의 판단` : '카드뉴스 한 건 완료!'}</h2>
            <p>
              {review ? '그날 낸 답과 채점 결과를 다시 봤어요.' : '오늘의 판단까지 기록했어요.'}
            </p>
          </div>

          <dl className="mm-scores">
            <Score label="종합 점수" value={total} main />
            <Score label="개념 이해도" value={concept} />
            <Score label="적용 판단" value={judgement} />
          </dl>

          <div className="mm-h-sec">
            <h3>오늘 한 것</h3>
          </div>
          <ul className="mm-did">
            {summaryLines(card, results).map((line) => (
              <li key={line}>
                <VerdictIcon ok />
                <span>{line}</span>
              </li>
            ))}
          </ul>

          {ghost.data?.comparison && <GhostCard card={card} comparison={ghost.data.comparison} />}

          {/* AI 피드백: 판단해보기 채점 결과 (모든 유형 공통) */}
          {grade && <AiAnalysis grade={grade} />}
        </div>
      </div>

      <div className="mm-l-foot">
        <Link to={primary.to} className="mm-btn">
          {primary.label}
        </Link>
        {SHOW_TAB2 && !review && (
          <Link to="/" className="mm-textbtn leading-10">
            홈으로
          </Link>
        )}
      </div>
    </div>
  )
}

/** 점수 한 칸. 채점된 것이 없으면 '-' */
const Score = ({
  label,
  value,
  main = false,
}: {
  label: string
  value: number | null
  main?: boolean
}) => {
  return (
    <div className={`mm-score ${main ? 'main' : ''}`}>
      <dt>{label}</dt>
      <dd>
        {value === null ? (
          '-'
        ) : (
          <>
            {value}
            <small>점</small>
          </>
        )}
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
