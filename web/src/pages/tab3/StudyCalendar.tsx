import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
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
 * 탭3 학습 달력. 문제를 푼 날(KST)에 남색 동그라미, 오늘은 진한 테두리.
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
      <h2 className="px-5 text-xl font-bold text-[#232c5c]">학습 달력</h2>
      <div
        ref={scroller}
        className="mt-4 flex snap-x snap-mandatory scroll-px-5 gap-3 overflow-x-auto px-5 pb-2"
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

      <div className="mt-5 px-5">
        {selected ? (
          <DayCards date={selected} cards={selectedCards} onClose={() => setSelected(null)} />
        ) : (
          <p className="rounded-3xl bg-[#fff3c4] px-5 py-4 text-sm leading-relaxed font-semibold text-[#232c5c]">
            {streakDays > 0
              ? `${streakDays}일째 이어가는 중이에요.`
              : '오늘 첫 카드뉴스를 풀어 볼까요?'}
            <br />
            남색 동그라미가 카드뉴스를 배운 날이에요. 누르면 다시 볼 수 있어요.
          </p>
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
    <div className="w-[88%] shrink-0 snap-start rounded-[28px] bg-white px-4 pt-5 pb-4 shadow-[0_6px_0_#dfe4f6]">
      <p className="text-center text-lg font-bold text-[#232c5c]">
        {y}년 {m}월
      </p>
      <div className="mt-3 grid grid-cols-7 text-center text-xs font-semibold text-[#5b6694]">
        {WEEKDAYS.map((w) => (
          <span key={w}>{w}</span>
        ))}
      </div>
      <div className="mt-2 grid grid-cols-7 gap-y-1.5">
        {monthCells(month).map((date, i) =>
          date === null ? (
            <span key={`e${i}`} />
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
  const base = 'mx-auto flex size-10 items-center justify-center rounded-full text-[15px] font-bold'

  if (!studied) {
    return (
      <span
        className={`${base} ${isFuture ? 'text-[#a3abcb]' : 'text-[#3a4473]'} ${
          isToday ? 'ring-2 ring-[#232c5c]' : ''
        }`}
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
      className={`${base} bg-[#5468b8] text-white active:scale-95 ${
        isSelected ? 'ring-4 ring-[#ffd84d]' : isToday ? 'ring-2 ring-[#232c5c] ring-offset-0' : ''
      }`}
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

/** 고른 날에 푼 카드뉴스. 카드뉴스 다시 보기 / 퀴즈 다시 풀기 */
const DayCards = ({ date, cards, onClose }: DayCardsProps) => {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h3 className="text-base font-bold text-[#232c5c]">{formatDay(date)}에 푼 카드뉴스</h3>
        <button type="button" onClick={onClose} className="text-xs font-semibold text-[#5b6694]">
          닫기
        </button>
      </div>
      <ul className="mt-3 space-y-3">
        {cards.map((c) => (
          <li key={c.cardId} className="rounded-3xl bg-white p-4 shadow-[0_4px_0_#dfe4f6]">
            {c.cardDate !== date && (
              <p className="text-[11px] font-semibold text-[#5468b8]">
                지난 뉴스 · {formatDay(c.cardDate)}
              </p>
            )}
            <p className="text-[15px] leading-snug font-bold text-[#232c5c]">{c.title}</p>
            <p className="mt-1 text-xs text-[#5b6694]">
              {c.stepCount > 0 ? `문제 ${c.stepCount}개 중 ${c.correct}개 맞힘` : '문제 없음'}
              {c.answered < c.stepCount && ` · ${c.stepCount - c.answered}개는 안 풀었어요`}
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm font-bold">
              <Link
                to={`/news/${c.cardId}`}
                className="rounded-2xl bg-[#e6eafa] py-2.5 text-center text-[#3a4a99]"
              >
                카드뉴스 보기
              </Link>
              <Link
                to={`/news/${c.cardId}/learn`}
                className="rounded-2xl bg-[#5468b8] py-2.5 text-center text-white"
              >
                퀴즈 다시 풀기
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
