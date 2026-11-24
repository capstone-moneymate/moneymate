import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import axios from 'axios'
import { useReviewQuiz, useReviews, useSubmitReviewAnswer } from '@/api/learner'
import { useAnswerMeter } from '@/lib/answerMeter'
import type { Confidence } from '@/types/card'
import type { ReviewItem, ReviewQuiz, ReviewQuizKind, ReviewResult } from '@/types/learner'
import { BackButton } from '@/pages/tab1/CloseLink'
import { AnswerFeedback } from '@/pages/tab1/steps/AnswerFeedback'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

const BACK = '/mypage?view=learn'

/**
 * 복습 문제 풀기 (추가 구현 2-4·2-7). 마이페이지 "오늘의 복습" 순서대로 개념마다 새 문제를 하나씩 푼다.
 * 문제는 서버가 그때 만들고(정답은 서버가 보관), 답을 내면 서버가 채점해 알 확률과 다음 복습일을 고친다.
 * 화면은 본 문제 퀴즈와 같다: 보기를 고르고 [헷갈려요] [확실해요] → 정답·해설 → 다음 개념.
 */
export const ReviewPage = () => {
  const reviews = useReviews()

  if (reviews.isPending) return <p className="p-5 text-sm text-slate-500">불러오는 중…</p>
  if (reviews.isError) {
    return (
      <Notice text="오늘의 복습을 불러오지 못했어요.">
        <BackLink />
      </Notice>
    )
  }
  if (reviews.data.items.length === 0) {
    return (
      <Notice text="오늘은 복습할 개념이 없어요.">
        <BackLink />
      </Notice>
    )
  }
  // 들어온 순간의 목록으로 끝까지 푼다 (푸는 동안 목록을 다시 읽어도 순서가 바뀌지 않게)
  return <ReviewSession items={reviews.data.items} />
}

interface Done {
  item: ReviewItem
  /** null = 건너뜀 (문제를 못 만들었거나 이미 복습한 개념) */
  result: ReviewResult | null
}

const ReviewSession = ({ items: initial }: { items: ReviewItem[] }) => {
  const [items] = useState(initial)
  const [done, setDone] = useState<Done[]>([])
  const navigate = useNavigate()
  const current = items[done.length]

  if (!current) return <ReviewSummary done={done} />

  return (
    <div className="flex min-h-full flex-col">
      <div className="flex items-center gap-4 px-5 pt-4">
        <BackButton label="마이페이지로 돌아가기" onClick={() => navigate(BACK)} />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-500">
            오늘의 복습 {done.length + 1} · {items.length}
          </p>
          <p className="truncate text-base font-bold text-slate-900">{current.concept}</p>
          <div className="mt-1.5 flex gap-1" aria-hidden>
            {items.map((item, i) => (
              <span
                key={item.nodeId}
                className={`h-1 w-6 rounded-full ${i <= done.length ? 'bg-primary' : 'bg-slate-200'}`}
              />
            ))}
          </div>
        </div>
      </div>
      <div className="flex flex-1 flex-col">
        {/* key: 개념이 바뀌면 고른 답과 시간을 새로 시작 */}
        <ReviewQuestion
          key={current.nodeId}
          item={current}
          last={done.length === items.length - 1}
          onDone={(result) => setDone([...done, { item: current, result }])}
        />
      </div>
    </div>
  )
}

interface ReviewQuestionProps {
  item: ReviewItem
  last: boolean
  onDone: (result: ReviewResult | null) => void
}

/** 개념 하나: 문제를 받아 오고(서버가 만든다), 받으면 푸는 화면을 그린다 */
const ReviewQuestion = ({ item, last, onDone }: ReviewQuestionProps) => {
  const quiz = useReviewQuiz(item.nodeId)
  const skipLabel = last ? '건너뛰고 끝내기' : '건너뛰고 다음 개념'

  if (quiz.isPending) {
    return <p className="p-5 text-sm text-slate-500">{item.concept} 문제를 만들고 있어요…</p>
  }
  if (quiz.isError) {
    // 409: 이미 복습했거나 오늘 목록에서 빠진 개념
    const gone = axios.isAxiosError(quiz.error) && quiz.error.response?.status === 409
    return (
      <Notice text={gone ? '이 개념은 이미 복습했어요.' : '문제를 만들지 못했어요.'}>
        {!gone && (
          <button
            type="button"
            onClick={() => quiz.refetch()}
            className="bg-primary w-full rounded-2xl py-4 font-bold text-white"
          >
            다시 시도
          </button>
        )}
        <button
          type="button"
          onClick={() => onDone(null)}
          className="min-h-11 w-full rounded-2xl bg-slate-100 py-4 font-bold text-slate-700"
        >
          {skipLabel}
        </button>
      </Notice>
    )
  }
  return <QuizBody quiz={quiz.data} last={last} onDone={onDone} />
}

const KIND_BADGE: Record<ReviewQuizKind, string> = {
  '용어 뜻': '뜻 고르기',
  '틀린 설명': '틀린 설명 찾기',
  'O/X': 'O/X',
}
const LETTERS = 'ABCDEFGH'

/** 문제 하나를 푸는 화면. 응답 시간은 문제가 화면에 뜬 순간(이 컴포넌트가 그려진 때)부터 잰다 */
const QuizBody = ({
  quiz,
  last,
  onDone,
}: {
  quiz: ReviewQuiz
  last: boolean
  onDone: (result: ReviewResult | null) => void
}) => {
  const [picked, setPicked] = useState<number | null>(null)
  const submit = useSubmitReviewAnswer()
  const meter = useAnswerMeter()
  const result = submit.data
  const ox = quiz.kind === 'O/X'

  const pick = (i: number) => {
    if (picked !== null && picked !== i) meter.changed()
    setPicked(i)
  }
  const check = (confidence: Confidence) => {
    if (picked === null) return
    submit.mutate({ quizId: quiz.quizId, answer: picked, meta: meter.read(confidence) })
  }

  return (
    <StepFrame
      badge={KIND_BADGE[quiz.kind] ?? quiz.kind}
      heading={ox ? quiz.content.statement : quiz.content.question}
      buttonLabel={last ? '복습 끝내기' : '다음 개념 ›'}
      onButton={() => onDone(result ?? null)}
      confidence={
        result ? undefined : { disabled: picked === null || submit.isPending, onPick: check }
      }
    >
      {ox && <p className="-mt-2 mb-4 text-sm text-slate-500">맞으면 O, 틀리면 X를 골라요</p>}
      <ul className={ox ? 'grid grid-cols-2 gap-3' : 'flex flex-col gap-3'}>
        {quiz.content.options.map((option, i) => (
          <li key={option}>
            <button
              type="button"
              disabled={!!result}
              onClick={() => pick(i)}
              className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-4 text-left font-semibold transition ${ox ? 'justify-center text-2xl' : ''} ${optionClass(i, picked, result)}`}
            >
              {!ox && (
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-white text-sm font-bold text-slate-600">
                  {LETTERS[i]}
                </span>
              )}
              {option}
            </button>
          </li>
        ))}
      </ul>
      {result && (
        <>
          <AnswerFeedback
            result={{
              stepId: String(quiz.quizId),
              isCorrect: result.correct,
              explanation: result.explanation,
            }}
            correctText={quiz.content.options[result.key]}
          />
          <p className="mt-3 text-sm text-slate-500">다음 복습은 {dayLabel(result.dueAt)}이에요</p>
        </>
      )}
      {submit.isError && (
        <p className="text-up mt-3 text-sm">채점하지 못했어요. 다시 눌러 주세요.</p>
      )}
    </StepFrame>
  )
}

/** 고르기 전·후 보기 색 (본 문제 퀴즈와 같다). 결과가 나오면 정답은 파랑, 내가 고른 오답은 빨강 테두리 */
const optionClass = (i: number, picked: number | null, result?: ReviewResult) => {
  if (result) {
    if (i === result.key) return 'border-primary bg-blue-50 text-slate-900'
    if (i === picked) return 'border-up bg-rose-50 text-slate-900'
    return 'border-transparent bg-slate-100 text-slate-400'
  }
  return i === picked
    ? 'border-primary bg-blue-50 text-slate-900'
    : 'border-transparent bg-slate-100 text-slate-800'
}

/** ISO 시각 → 'M월 D일' (한국 날짜) */
const dayLabel = (iso: string): string =>
  new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    month: 'long',
    day: 'numeric',
  }).format(new Date(iso))

/** 다 푼 뒤: 개념마다 맞힘·틀림과 다음 복습일. 사실만 적는다 */
const ReviewSummary = ({ done }: { done: Done[] }) => {
  const answered = done.filter((d) => d.result)
  const right = answered.filter((d) => d.result?.correct).length

  return (
    <div className="flex min-h-full flex-col px-5 pt-8 pb-5">
      <h2 className="text-2xl leading-snug font-bold text-slate-900">
        오늘의 복습,
        <br />
        {answered.length}개 중 {right}개 맞혔어요
      </h2>
      <ul className="mt-6 flex flex-col gap-2">
        {done.map(({ item, result }) => (
          <li
            key={item.nodeId}
            className="flex items-center justify-between gap-3 rounded-2xl bg-slate-100 px-4 py-3.5"
          >
            <div className="min-w-0">
              <p className="truncate font-bold text-slate-900">{item.concept}</p>
              <p className="mt-0.5 text-xs text-slate-500">
                {result ? `다음 복습 ${dayLabel(result.dueAt)}` : '건너뛰었어요'}
              </p>
            </div>
            {result && (
              <span
                className={`shrink-0 text-sm font-bold ${result.correct ? 'text-primary' : 'text-up'}`}
              >
                {result.correct ? '맞힘' : '틀림'}
              </span>
            )}
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs break-keep text-slate-500">
        맞힌 개념은 복습 간격이 벌어지고, 틀린 개념은 내일 다시 나와요.
      </p>
      <div className="mt-auto pt-7">
        <BackLink />
      </div>
    </div>
  )
}

const Notice = ({ text, children }: { text: string; children: React.ReactNode }) => (
  <div className="flex flex-1 flex-col gap-3 p-5">
    <p className="text-sm text-slate-500">{text}</p>
    {children}
  </div>
)

const BackLink = () => (
  <Link
    to={BACK}
    className="bg-primary block w-full rounded-2xl py-4 text-center font-bold text-white"
  >
    마이페이지로
  </Link>
)
