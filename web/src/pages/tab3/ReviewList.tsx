import { useState } from 'react'
import type { ReviewConcept } from '@/types/causalMap'

/** 처음에 보여 줄 줄 수. 나머지는 "전체 보기"로 편다 */
const FIRST_ROWS = 5

interface ReviewListProps {
  concepts: ReviewConcept[]
  /** 한 줄을 누르면 인과 지도에서 그 개념을 연다 */
  onOpen: (conceptId: string) => void
}

/**
 * 마이페이지 홈의 "다시 보는 개념" (시안 26). 서버가 정렬한 순서(종합 정답률 낮은 순 → 푼 횟수 적은 순 → id 순) 그대로.
 * 정답률은 객관식 정답과 판단해보기 60점 이상을 함께 센 user_concepts 의 correct/total 이다.
 * 숫자는 받은 correct·total·accuracy 만 쓰고, 화면은 % 로 바꿔 표기만 한다.
 */
export const ReviewList = ({ concepts, onOpen }: ReviewListProps) => {
  const [expanded, setExpanded] = useState(false)
  const shown = expanded ? concepts : concepts.slice(0, FIRST_ROWS)

  return (
    <section className="mt-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-base font-bold text-slate-900">다시 보는 개념</h2>
        <p className="text-xs text-slate-500">{concepts.length}개</p>
      </div>
      {concepts.length === 0 ? (
        <p className="mt-3 rounded-2xl bg-slate-50 px-4 py-5 text-center text-xs text-slate-500">
          탭 1에서 뉴스 문제를 풀면 정답률이 낮은 개념부터 여기에 모여요
        </p>
      ) : (
        <>
          <ul className="mt-3 space-y-2">
            {shown.map((c) => (
              <li key={c.id}>
                <ReviewRow concept={c} onOpen={() => onOpen(c.id)} />
              </li>
            ))}
          </ul>
          {concepts.length > FIRST_ROWS && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="mt-2 w-full py-2 text-xs font-semibold text-slate-500"
            >
              {expanded ? '접기' : `전체 보기 (${concepts.length}개)`}
            </button>
          )}
        </>
      )}
    </section>
  )
}

const ReviewRow = ({ concept, onOpen }: { concept: ReviewConcept; onOpen: () => void }) => {
  const percent = Math.round(concept.accuracy * 100)
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={`${concept.name}, 정답률 ${percent}%, 인과 지도에서 보기`}
      className="flex w-full items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3.5 text-left active:bg-slate-100"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold text-slate-900">{concept.name}</p>
        <p className="mt-0.5 text-xs text-slate-500">
          {concept.theme} · 정답률 {percent}%
        </p>
      </div>
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        className="shrink-0 text-slate-400"
        aria-hidden
      >
        <path d="m9 18 6-6-6-6" />
      </svg>
    </button>
  )
}
