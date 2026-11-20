import { useState } from 'react'
import { Link } from 'react-router'
import type { StockChart } from '@/types/news'

type Pick = 'up' | 'down'

interface UpDownQuizProps {
  chart: StockChart
}

/**
 * 차트 아래 O/X 퀴즈: "오늘 NVDA, 어제보다 올랐을까요?"
 * 정답은 코드가 정한다: 오늘 종가(todayClose) > 어제 종가 → O, < → X, 같으면 둘 다 아님.
 * 장 마감 전(todayClose = null)에는 고른 것만 기억하고, 마감 뒤에 정답·등락률을 보여 준다.
 * 고른 답은 아직 서버 API 가 없어서 이 기기에만 저장한다(localStorage).
 */
export const UpDownQuiz = ({ chart }: UpDownQuizProps) => {
  const key = `mm:updown:${chart.ticker}:${chart.today}`
  const [pick, setPick] = useState<Pick | null>(() => loadPick(key))
  const yesterday = chart.candles[chart.candles.length - 1]
  const closed = chart.todayClose !== null && yesterday !== undefined
  const chg = closed ? chart.todayClose! / yesterday.close - 1 : null
  const answer: Pick | 'flat' | null =
    chg === null ? null : chg > 0 ? 'up' : chg < 0 ? 'down' : 'flat'

  const choose = (next: Pick) => {
    if (closed) return // 마감 뒤에는 바꿀 수 없다
    setPick(next)
    savePick(key, next)
  }

  return (
    <div className="mt-3 border-t border-slate-100 pt-3">
      <div>
        {/* 390px 폭에서 질문이 세 줄로 꺾이지 않게 질문 한 줄, 버튼은 아래 반반 */}
        <p className="text-[15px] leading-snug font-bold break-keep text-slate-900">
          오늘 {chart.ticker}, 어제보다 올랐을까요?
        </p>
        <div
          className="mt-2.5 grid grid-cols-2 gap-2"
          role="group"
          aria-label="오늘 올랐을지 고르기"
        >
          <QuizButton
            kind="up"
            picked={pick === 'up'}
            dimmed={pick !== null && pick !== 'up'}
            disabled={closed}
            onClick={() => choose('up')}
          />
          <QuizButton
            kind="down"
            picked={pick === 'down'}
            dimmed={pick !== null && pick !== 'down'}
            disabled={closed}
            onClick={() => choose('down')}
          />
        </div>
      </div>

      <QuizResult chart={chart} pick={pick} answer={answer} chg={chg} />
    </div>
  )
}

interface QuizButtonProps {
  kind: Pick
  picked: boolean
  dimmed: boolean
  disabled: boolean
  onClick: () => void
}

const QuizButton = ({ kind, picked, dimmed, disabled, onClick }: QuizButtonProps) => {
  const up = kind === 'up'
  const base = up
    ? 'border-rose-300 bg-rose-50 text-rose-600'
    : 'border-indigo-300 bg-indigo-50 text-indigo-700'
  const active = up
    ? 'border-rose-500 bg-rose-500 text-white'
    : 'border-indigo-600 bg-indigo-600 text-white'
  return (
    <button
      type="button"
      aria-pressed={picked}
      disabled={disabled}
      onClick={onClick}
      className={`min-h-12 rounded-2xl border-2 px-3.5 text-[15px] font-bold transition active:scale-95 disabled:cursor-default ${
        picked ? active : base
      } ${dimmed ? 'opacity-40' : ''}`}
    >
      {up ? 'O 오른다' : 'X 내린다'}
    </button>
  )
}

interface QuizResultProps {
  chart: StockChart
  pick: Pick | null
  answer: Pick | 'flat' | null
  chg: number | null
}

/** 고른 뒤 한 줄 안내 / 마감 뒤 정답 */
const QuizResult = ({ chart, pick, answer, chg }: QuizResultProps) => {
  if (answer === null || chg === null) {
    if (!pick) return null
    return (
      <p role="status" className="mt-2 text-xs text-slate-500">
        <b className="text-slate-700">{pick === 'up' ? 'O 오른다' : 'X 내린다'}</b>를 골랐어요.{' '}
        {closeText(chart.market, chart.today)} 정답을 알려 드려요. 그 전에는 바꿀 수 있어요.
      </p>
    )
  }

  const moved =
    answer === 'flat'
      ? '어제와 같은 값으로 마감했어요'
      : `${(Math.abs(chg) * 100).toFixed(2)}% ${answer === 'up' ? '올랐어요' : '내렸어요'}`
  const head = !pick ? '오늘은' : pick === answer ? '정답! 오늘은' : '아쉬워요. 오늘은'
  const tone = answer === 'up' ? 'text-up' : answer === 'down' ? 'text-down' : 'text-slate-600'

  return (
    <div role="status" className="mt-2 rounded-2xl bg-slate-50 px-3.5 py-3 text-sm">
      <p className="font-semibold text-slate-800">
        {head} <span className={tone}>{moved}</span>
      </p>
      {chart.todayCardId && (
        <Link
          to={`/news/${chart.todayCardId}`}
          className="text-primary mt-1 inline-flex min-h-9 items-center text-sm font-semibold"
        >
          왜 그런지 카드뉴스로 ›
        </Link>
      )}
    </div>
  )
}

const loadPick = (key: string): Pick | null => {
  try {
    const v = localStorage.getItem(key)
    return v === 'up' || v === 'down' ? v : null
  } catch {
    return null // 사생활 보호 모드 등에서는 저장을 못 한다
  }
}

const savePick = (key: string, value: Pick) => {
  try {
    localStorage.setItem(key, value)
  } catch {
    // 저장 못 해도 화면에서는 고른 상태로 보인다
  }
}

/**
 * 장 마감 시각 안내 (한국 시각).
 * 국내: 그날 15:30. 미국: 뉴욕 16:00 = 한국 다음 날 06:00, 서머타임(3월 둘째 일요일~11월 첫째 일요일)이면 05:00.
 */
const closeText = (market: StockChart['market'], today: string) => {
  if (market === 'KR') return '오늘 오후 3시 30분 장이 끝나면'
  const [y, m, d] = today.split('-').map(Number)
  const closeUtcHour = isUsDst(y, m, d) ? 20 : 21 // 뉴욕 16:00 = UTC 20시(서머타임) / 21시
  const kst = new Date(Date.UTC(y, m - 1, d, closeUtcHour + 9)) // 한국 = UTC+9
  const day = '일월화수목금토'[kst.getUTCDay()]
  return `미국 장이 끝나는 ${kst.getUTCMonth() + 1}/${kst.getUTCDate()}(${day}) 오전 ${kst.getUTCHours()}시(한국 시각)에`
}

/** 미국 서머타임 기간인가: 3월 둘째 일요일 ~ 11월 첫째 일요일 전날 */
const isUsDst = (y: number, m: number, d: number) => {
  const nthSunday = (month: number, n: number) => {
    const first = new Date(Date.UTC(y, month - 1, 1)).getUTCDay()
    return 1 + ((7 - first) % 7) + (n - 1) * 7
  }
  const t = Date.UTC(y, m - 1, d)
  return t >= Date.UTC(y, 2, nthSunday(3, 2)) && t < Date.UTC(y, 10, nthSunday(11, 1))
}
