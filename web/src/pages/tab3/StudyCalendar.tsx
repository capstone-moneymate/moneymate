import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import { Mate } from '@/components/Mate'
import { withReview } from '@/lib/review'
import type { CalendarCard, CalendarDay } from '@/types/causalMap'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

/** 오늘 날짜 (KST, yyyy-MM-dd). 서버가 날짜를 KST 로 자르므로 화면도 KST 로 맞춘다 */
const todayKst = (): string => new Date(Date.now() + 9 * 3600_000).toISOString().slice(0, 10)

const pad = (n: number) => String(n).padStart(2, '0')

/** 'yyyy-MM' 두 달 사이(양끝 포함)의 달 목록 */
const monthsBetween = (from: string, to: string): string[] => {
  let [y, m] = from.split('-').map(Number)
  const [ty, tm] = to.split('-').map(Number)
  const out: string[] = []
  while (y < ty || (y === ty && m <= tm)) {
    out.push(`${y}-${pad(m)}`)
    m += 1
    if (m > 12) {
      m = 1
      y += 1
    }
  }
  return out
}

/** 그 달 칸 목록. 앞쪽 빈칸은 null (일요일 시작) */
const monthCells = (month: string): (string | null)[] => {
  const [y, m] = month.split('-').map(Number)
  const firstDow = new Date(Date.UTC(y, m - 1, 1)).getUTCDay()
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate()
  return [
    ...Array<null>(firstDow).fill(null),
    ...Array.from({ length: days }, (_, i) => `${month}-${pad(i + 1)}`),
  ]
}

const formatDay = (date: string): string => {
  const [y, m, d] = date.split('-').map(Number)
  const dow = WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]
  return `${m}월 ${d}일 (${dow})`
}

interface StudyCalendarProps {
  days: CalendarDay[]
  streakDays: number
}

/**
 * 탭3 학습 달력 (UI 시안 app.html 의 달력). 문제를 푼 날(KST)에 파란 동그라미, 오늘은 진한 테두리.
 * 달은 옆으로 밀어 넘기고(처음엔 이번 달), 동그라미 날을 누르면 그날 푼 카드뉴스가 아래에 나온다.
 */
export const StudyCalendar = ({ days, streakDays }: StudyCalendarProps) => {
  const today = todayKst()
  const byDate = useMemo(() => new Map(days.map((d) => [d.date, d.cards])), [days])
  const months = useMemo(() => {
    const thisMonth = today.slice(0, 7)
    const first = days.reduce((min, d) => (d.date < min ? d.date : min), today).slice(0, 7)
    return monthsBetween(first, thisMonth)
  }, [days, today])
  const [selected, setSelected] = useState<string | null>(null)
  const scroller = useRef<HTMLDivElement>(null)

  // 처음 열면 이번 달(맨 오른쪽)을 보여 준다
  useEffect(() => {
    const el = scroller.current
    if (el) el.scrollLeft = el.scrollWidth
  }, [months.length])

  const selectedCards = selected ? (byDate.get(selected) ?? []) : []

  return (
    <section>
      <h2 className="px-5 text-xl font-extrabold tracking-[-0.02em]">학습 달력</h2>
      <div
        ref={scroller}
        className="mt-2.5 flex snap-x snap-mandatory scroll-px-5 gap-2.5 overflow-x-auto px-5 pt-0.5 pb-1.5"
      >
        {months.map((month) => (
          <MonthGrid
            key={month}
            month={month}
            today={today}
            studied={byDate}
            selected={selected}
            onSelect={(d) => setSelected((cur) => (cur === d ? null : d))}
          />
        ))}
      </div>

      <div className="mt-3 px-5">
        {selected ? (
          <DayCards date={selected} cards={selectedCards} onClose={() => setSelected(null)} />
        ) : (
          <div className="mm-note">
            <Mate mood={streakDays > 0 ? 'wink' : 'smile'} />
            <p>
              {streakDays > 0
                ? `${streakDays}일째 이어가는 중이에요.`
                : '오늘 첫 카드뉴스를 풀어 볼까요?'}
              <br />
              파란 날짜를 누르면 그날 문제를 다시 볼 수 있어요.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}

interface MonthGridProps {
  month: string
  today: string
  studied: Map<string, CalendarCard[]>
  selected: string | null
  onSelect: (date: string) => void
}

const MonthGrid = ({ month, today, studied, selected, onSelect }: MonthGridProps) => {
  const [y, m] = month.split('-').map(Number)
  return (
    <div className="mm-box w-[90%] shrink-0 snap-center px-3 pt-4 pb-3.5">
      <p className="text-center text-[17px] font-extrabold">
        {y}년 {m}월
      </p>
      <div className="mm-cal">
        {WEEKDAYS.map((w) => (
          <span key={w}>{w}</span>
        ))}
        {monthCells(month).map((date, i) =>
          date === null ? (
            <i key={`e${i}`} />
          ) : (
            <DayCell
              key={date}
              date={date}
              isToday={date === today}
              isFuture={date > today}
              cards={studied.get(date)}
              isSelected={date === selected}
              onSelect={onSelect}
            />
          ),
        )}
      </div>
    </div>
  )
}

interface DayCellProps {
  date: string
  isToday: boolean
  isFuture: boolean
  cards: CalendarCard[] | undefined
  isSelected: boolean
  onSelect: (date: string) => void
}

const DayCell = ({ date, isToday, isFuture, cards, isSelected, onSelect }: DayCellProps) => {
  const day = Number(date.slice(8))
  const studied = !!cards?.length

  if (!studied) {
    return (
      <span
        className={`d ${isFuture ? 'future' : ''} ${isToday ? 'today' : ''}`}
        aria-label={isToday ? `오늘 ${day}일` : undefined}
      >
        {day}
      </span>
    )
  }

  return (
    <button
      type="button"
      onClick={() => onSelect(date)}
      aria-pressed={isSelected}
      aria-label={`${formatDay(date)} 카드뉴스 ${cards.length}장 다시 보기`}
      className={`d ${isToday ? 'today' : ''}`}
    >
      {day}
    </button>
  )
}

interface DayCardsProps {
  date: string
  cards: CalendarCard[]
  onClose: () => void
}

/** 고른 날에 푼 카드뉴스. 풀었던 내용 보기(그날 답 그대로) / 퀴즈 다시 풀기(처음 상태) */
const DayCards = ({ date, cards, onClose }: DayCardsProps) => {
  return (
    <div aria-live="polite">
      <div className="flex items-baseline justify-between">
        <h3 className="text-[15px] font-extrabold">{formatDay(date)}에 푼 카드뉴스</h3>
        <button type="button" onClick={onClose} className="text-sub text-xs font-bold">
          닫기
        </button>
      </div>
      <ul className="mt-2 space-y-2">
        {cards.map((c) => (
          <li key={c.cardId} className="mm-box p-3.5">
            {c.cardDate !== date && (
              <p className="text-blue-ink text-[11.5px] font-extrabold">
                지난 뉴스 · {formatDay(c.cardDate)}
              </p>
            )}
            <p className="text-[15px] leading-snug font-extrabold">{c.title}</p>
            <p className="text-sub mt-1 text-xs font-semibold">
              {c.stepCount > 0 ? `문제 ${c.stepCount}개 중 ${c.correct}개 맞힘` : '문제 없음'}
              {c.answered < c.stepCount && ` · ${c.stepCount - c.answered}개는 안 풀었어요`}
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {/* 둘 다 카드뉴스부터 시작해 퀴즈로 이어진다. 보기는 그날 낸 답·채점 결과를 채워서, 다시 풀기는 처음 상태로 */}
              <Link to={withReview(`/news/${c.cardId}`, date)} className="mm-btn sm ghost">
                풀었던 내용 보기
              </Link>
              <Link to={`/news/${c.cardId}`} className="mm-btn sm">
                퀴즈 다시 풀기
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
