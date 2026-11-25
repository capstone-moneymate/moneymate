import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useCard } from '@/api/cards'
import { Mate } from '@/components/Mate'
import { reviewLabel, useReviewDate, withReview } from '@/lib/review'
import { LessonTop } from '@/pages/tab1/LessonTop'

const MOODS = ['hi', 'think', 'smile'] as const

/**
 * 카드뉴스: 2~3장을 한 장씩 넘긴 뒤 단계형 학습으로 들어간다 (서비스흐름 2.1, UI 시안 app.html 의 뉴스 장).
 * 위 진행 막대는 카드뉴스 장과 학습 단계를 합쳐 지금 어디인지 보여 준다 (학습 화면과 이어진다).
 * ?review=날짜(탭3 풀었던 내용 보기)면 학습 화면에도 그대로 넘겨 그날 낸 답을 보여 준다
 */
export const CardNewsPage = () => {
  const { cardId = '' } = useParams()
  const navigate = useNavigate()
  const { data: card, isPending, isError } = useCard(cardId)
  const [index, setIndex] = useState(0)
  const review = useReviewDate()

  if (isPending) return <p className="text-sub p-5 text-sm font-semibold">불러오는 중…</p>
  if (isError) {
    return (
      <div className="text-sub p-5 text-sm font-semibold">
        카드를 찾을 수 없어요.{' '}
        <Link to="/" className="text-blue-ink underline">
          뉴스 홈으로
        </Link>
      </div>
    )
  }

  const slide = card.slides[index]
  const total = card.slides.length
  const isLast = index === total - 1

  return (
    <div className="flex h-full flex-col">
      <LessonTop
        progress={((index + 1) / (total + card.steps.length)) * 100}
        onBack={index > 0 ? () => setIndex(index - 1) : undefined}
        backLabel="이전 카드"
      />

      <div className="min-h-0 flex-1 overflow-y-auto">
        {/* key: 장이 바뀌면 내용이 옆에서 다시 들어온다 */}
        <div className="mm-l-body" key={index}>
          <div className="flex flex-wrap gap-1.5">
            <span className="mm-chip butter">
              {review ? `풀었던 내용 · ${reviewLabel(review)}` : '카드뉴스'} {index + 1} / {total}
            </span>
            {card.theme && <span className="mm-chip gray">{card.theme}</span>}
          </div>
          <div className="mm-nstage" aria-hidden>
            <Mate mood={MOODS[index % MOODS.length]} />
          </div>
          <p className="text-sub mt-5 text-[14.5px] font-bold">{slide.label}</p>
          <h2 className="mt-1 text-[30px] leading-[1.24] font-extrabold tracking-[-0.03em] whitespace-pre-line">
            {slide.heading}
          </h2>
          <p className="text-sub mt-2.5 text-[16.5px] leading-[1.6] font-medium">{slide.body}</p>
          {slide.facts && (
            <dl className="mm-nstats">
              {slide.facts.map((fact) => (
                <div key={fact.label}>
                  <dt>{fact.label}</dt>
                  <dd>
                    <b>{fact.value}</b>
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>

      <div className="mm-l-foot">
        <button
          type="button"
          onClick={() =>
            isLast ? navigate(withReview(`/news/${card.id}/learn`, review)) : setIndex(index + 1)
          }
          className="mm-btn"
        >
          {isLast ? (review ? '풀었던 퀴즈 보기' : '개념 배우러 가기') : '다음'}
        </button>
        <p className="text-faint text-center text-xs font-medium">
          출처{' '}
          <a href={card.sourceUrl} target="_blank" rel="noreferrer" className="underline">
            {card.sourceName}
          </a>{' '}
          · 카드 문장은 AI가 쓰고 숫자는 원자료로 계산했어요
        </p>
      </div>
    </div>
  )
}
