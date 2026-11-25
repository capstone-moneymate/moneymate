import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  LineSeries,
  LineStyle,
  createChart,
} from 'lightweight-charts'
import type { IChartApi, ISeriesApi, Time } from 'lightweight-charts'
import { UpDownQuiz } from '@/pages/tab1/UpDownQuiz'
import type { Candle, StockChart, StockChartNote } from '@/types/news'

/** 오른 날 빨강, 내린 날 파랑, 5일선 노랑, 지난 카드뉴스 ○ 파랑 (styles/index.css 의 up·down·butter·blue 와 같은 값) */
const UP = '#f0506a'
const DOWN = '#4f63d2'
const MA5 = '#ffc94d'
const RING = '#3b8dff'
const CHART_HEIGHT = 200
const VISIBLE_DAYS = 20
/** 이 시간(ms) 이상 누르고 있으면 말풍선을 연다 */
const LONG_PRESS_MS = 350
/** 누르기 전에 이만큼(px) 움직이면 스크롤로 보고 꾹 누르기를 취소한다 */
const MOVE_TOLERANCE = 10

interface StockChartCardProps {
  chart: StockChart
}

/** 차트 위에 HTML 로 얹는 것들의 위치 (lightweight-charts 좌표 → px) */
interface Layout {
  /** 화면에 그린 날마다 x (마지막 하나는 오늘 빈 칸) */
  xs: number[]
  barWidth: number
  /** 차트 전체 폭 (말풍선이 밖으로 안 나가게) */
  width: number
  /** ○ 를 띄울 날의 y (그날 고가 위) */
  ringYs: Record<string, number>
}

/**
 * 탭1 홈 종목 차트 카드: 최근 20거래일 일봉 + 어제 종가 점선 + 5일선.
 * - 지난 카드뉴스가 있던 날 위에 파란 ○ (누르면 그 카드뉴스로)
 * - 꾹 누르면 그날 등락률과 이유 말풍선, 누른 채로 밀면 날짜가 바뀐다
 * - 오른쪽 끝 '오늘' 칸을 누르면 오늘의 카드뉴스로
 * 숫자(등락률·5일선)는 코드가 계산하고, 이유 문장만 데이터(notes)에서 가져온다.
 */
export const StockChartCard = ({ chart }: StockChartCardProps) => {
  const candles = chart.candles
  const shown = candles.slice(-VISIBLE_DAYS)
  const last = candles[candles.length - 1]
  const prev = candles[candles.length - 2]
  const chg = last && prev ? last.close / prev.close - 1 : null

  return (
    <section className="mm-box p-3.5" aria-label="TOP 1 종목">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="mm-chip">TOP 1 종목</span>
          <b className="font-display text-xl leading-none font-normal">{chart.ticker}</b>
          <span className="text-sub truncate text-[13.5px] font-semibold">{chart.name}</span>
        </div>
        {last && (
          <div className="shrink-0 text-right">
            <p className="font-display text-[22px] leading-[1.1] whitespace-nowrap tabular-nums">
              {formatPrice(last.close, chart.market)}
            </p>
            {chg !== null && <ChangeText chg={chg} className="mt-1 block text-[13px]" />}
          </div>
        )}
      </div>

      <p className="text-sub mt-2 flex flex-wrap items-center gap-2.5 text-xs font-semibold">
        <span>최근 {shown.length}거래일</span>
        <span className="flex items-center gap-1">
          <span aria-hidden className="border-faint w-3.5 border-t-2 border-dashed" />
          어제 종가
        </span>
        <span className="flex items-center gap-1">
          <span aria-hidden className="h-[2.5px] w-3.5 rounded" style={{ background: MA5 }} />
          5일선
        </span>
      </p>

      <CandleChart chart={chart} />

      <p className="text-faint mt-1.5 flex items-center gap-1 text-xs font-semibold">
        꾹 눌러 밀면 날짜별 이유 ·
        <span
          aria-hidden
          className="inline-block size-2.5 rounded-full border-2"
          style={{ borderColor: RING }}
        />
        지난 카드뉴스
      </p>

      <UpDownQuiz key={`${chart.ticker}:${chart.today}`} chart={chart} />
    </section>
  )
}

const CandleChart = ({ chart }: StockChartCardProps) => {
  const navigate = useNavigate()
  const containerRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const [layout, setLayout] = useState<Layout | null>(null)
  /** 말풍선을 연 날 (shown 의 index) */
  const [selected, setSelected] = useState<number | null>(null)

  const shown = useMemo(() => chart.candles.slice(-VISIBLE_DAYS), [chart.candles])
  const notesByDate = useMemo(() => {
    const map = new Map<string, StockChartNote>()
    for (const note of chart.notes) map.set(note.date, note)
    return map
  }, [chart.notes])
  const ringDates = useMemo(
    () => shown.filter((c) => notesByDate.get(c.date)?.pastCardId).map((c) => c.date),
    [shown, notesByDate],
  )

  // 차트 위 HTML(○, 오늘 칸, 날짜, 말풍선) 위치를 다시 잰다
  const measure = useCallback(() => {
    const c = chartRef.current
    const series = seriesRef.current
    if (!c || !series) return
    const ts = c.timeScale()
    const dates = [...shown.map((d) => d.date), chart.today]
    const xs = dates.map((d) => ts.timeToCoordinate(d as Time) ?? NaN)
    if (xs.some(Number.isNaN)) return
    const ringYs: Record<string, number> = {}
    for (const date of ringDates) {
      const candle = shown.find((d) => d.date === date)
      const y = candle ? series.priceToCoordinate(candle.high) : null
      if (y !== null) ringYs[date] = y
    }
    const barWidth = xs.length > 1 ? xs[1] - xs[0] : 12
    // 왼쪽 가격 눈금 폭만큼 오버레이도 밀어야 해서 차트 영역 기준 x 로 바꾼다
    const offset = c.priceScale('left').width()
    setLayout({
      xs: xs.map((x) => x + offset),
      barWidth,
      width: c.options().width || (containerRef.current?.clientWidth ?? 0),
      ringYs,
    })
  }, [shown, chart.today, ringDates])

  useEffect(() => {
    if (!containerRef.current) return
    const c = createChart(containerRef.current, {
      autoSize: true,
      // 홈 스크롤을 차트가 가로채지 않게 확대·이동은 끈다 (꾹 누르기는 오버레이가 받는다)
      handleScroll: false,
      handleScale: false,
      layout: {
        attributionLogo: false, // 출처 표기는 마이페이지 오픈소스 라이선스(components/OpenSourceNotice)에 모았다
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9aa4b5',
        fontSize: 11,
      },
      grid: { vertLines: { visible: false }, horzLines: { color: '#e3e8ef' } },
      leftPriceScale: {
        visible: true,
        borderVisible: false,
        scaleMargins: { top: 0.18, bottom: 0.08 },
      },
      rightPriceScale: { visible: false },
      timeScale: { visible: false, fixLeftEdge: true, fixRightEdge: true },
      crosshair: { mode: CrosshairMode.Hidden },
      // 눈금은 정수로 (195, 185 …). 말풍선은 소수 둘째 자리까지 따로 쓴다
      localization: { priceFormatter: (p: number) => Math.round(p).toLocaleString('ko-KR') },
    })
    const series = c.addSeries(CandlestickSeries, {
      priceScaleId: 'left',
      upColor: UP,
      downColor: DOWN,
      borderVisible: false,
      wickUpColor: UP,
      wickDownColor: DOWN,
      lastValueVisible: false,
      priceLineVisible: false,
    })
    // 오늘은 아직 마감 전이라 빈 칸(whitespace)으로 자리만 잡는다
    series.setData([
      ...shown.map((d) => ({
        time: d.date as Time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      })),
      { time: chart.today as Time },
    ])
    const yesterday = shown[shown.length - 1]
    if (yesterday) {
      series.createPriceLine({
        price: yesterday.close,
        color: '#9aa4b5',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: false,
      })
    }
    const ma = c.addSeries(LineSeries, {
      priceScaleId: 'left',
      color: MA5,
      lineWidth: 2,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    })
    const shownDates = new Set(shown.map((d) => d.date))
    ma.setData(
      movingAverage(chart.candles, 5)
        .filter((p) => shownDates.has(p.date))
        .map((p) => ({ time: p.date as Time, value: p.value })),
    )
    c.timeScale().fitContent()

    chartRef.current = c
    seriesRef.current = series
    const ts = c.timeScale()
    ts.subscribeSizeChange(measure)
    ts.subscribeVisibleLogicalRangeChange(measure)
    // 가격 눈금 폭이 첫 그리기 뒤에 정해져서 한 번 더 잰다
    const frame = requestAnimationFrame(measure)
    const late = window.setTimeout(measure, 80)
    return () => {
      cancelAnimationFrame(frame)
      window.clearTimeout(late)
      ts.unsubscribeSizeChange(measure)
      ts.unsubscribeVisibleLogicalRangeChange(measure)
      chartRef.current = null
      seriesRef.current = null
      c.remove()
    }
  }, [chart.candles, chart.today, shown, measure])

  // ── 꾹 누르기 ──
  const press = useRef<{ x: number; y: number; timer: number | null; active: boolean } | null>(null)

  /** 오버레이 기준 x → 가장 가까운 날 index (오늘 빈 칸 제외) */
  const indexAt = useCallback(
    (clientX: number) => {
      const box = overlayRef.current?.getBoundingClientRect()
      if (!layout || !box) return null
      const x = clientX - box.left
      let best = 0
      for (let i = 1; i < shown.length; i += 1) {
        if (Math.abs(layout.xs[i] - x) < Math.abs(layout.xs[best] - x)) best = i
      }
      return best
    },
    [layout, shown.length],
  )

  // 말풍선을 연 채로 손가락을 위아래로 밀어도 페이지가 스크롤되지 않게 (passive: false 가 필요해서 직접 단다)
  useEffect(() => {
    const el = overlayRef.current
    if (!el) return
    const block = (e: TouchEvent) => {
      if (press.current?.active) e.preventDefault()
    }
    el.addEventListener('touchmove', block, { passive: false })
    return () => el.removeEventListener('touchmove', block)
  }, [])

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    const { clientX, clientY, pointerId } = e
    const target = e.currentTarget
    const timer = window.setTimeout(() => {
      if (!press.current) return
      press.current.active = true
      press.current.timer = null
      try {
        target.setPointerCapture(pointerId) // 손가락이 차트 밖으로 나가도 계속 따라간다
      } catch {
        // 이미 끝난 포인터면 잡지 못한다. 말풍선은 그대로 연다
      }
      navigator.vibrate?.(10)
      setSelected(indexAt(clientX))
    }, LONG_PRESS_MS)
    press.current = { x: clientX, y: clientY, timer, active: false }
  }

  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const p = press.current
    if (!p) return
    if (p.active) {
      setSelected(indexAt(e.clientX))
    } else if (Math.hypot(e.clientX - p.x, e.clientY - p.y) > MOVE_TOLERANCE) {
      cancelPress()
    }
  }

  const cancelPress = () => {
    if (press.current?.timer) window.clearTimeout(press.current.timer)
    press.current = null
  }

  const onPointerUp = (e: ReactPointerEvent<HTMLDivElement>) => {
    const p = press.current
    if (!p) return
    const wasLong = p.active
    cancelPress()
    if (wasLong) return // 말풍선은 손을 떼도 남겨 둔다
    onTap(e.clientX, e.clientY)
  }

  /** 짧게 탭: 말풍선이 열려 있으면 닫고, 아니면 오늘 칸 → 오늘 카드, ○ → 지난 카드 */
  const onTap = (clientX: number, clientY: number) => {
    if (selected !== null) {
      setSelected(null)
      return
    }
    const box = overlayRef.current?.getBoundingClientRect()
    if (!layout || !box) return
    const x = clientX - box.left
    const y = clientY - box.top
    const todayX = layout.xs[layout.xs.length - 1]
    if (chart.todayCardId && Math.abs(x - todayX) <= Math.max(layout.barWidth / 2, 14)) {
      navigate(`/news/${chart.todayCardId}`)
      return
    }
    for (const [date, ry] of Object.entries(layout.ringYs)) {
      const i = shown.findIndex((d) => d.date === date)
      const rx = layout.xs[i]
      if (Math.hypot(x - rx, y - (ry - RING_GAP)) <= 18) {
        const cardId = notesByDate.get(date)?.pastCardId
        if (cardId) navigate(`/news/${cardId}`)
        return
      }
    }
  }

  const sel = selected !== null ? shown[selected] : null
  const selPrev =
    selected !== null && selected > 0 ? shown[selected - 1] : prevOf(chart.candles, sel)

  return (
    <div className="relative mt-2" style={{ height: CHART_HEIGHT + 22 }}>
      <div
        ref={containerRef}
        role="img"
        aria-label={`${chart.name} 최근 ${shown.length}거래일 일봉 차트`}
        className="absolute top-0 right-3 left-0"
        style={{ height: CHART_HEIGHT }}
      />

      {layout && (
        <>
          {/* 오늘 칸: 아직 마감 전 */}
          <div
            aria-hidden
            className="bg-butter-soft pointer-events-none absolute top-1 rounded-md"
            style={{
              left: layout.xs[layout.xs.length - 1] - Math.max(layout.barWidth * 0.4, 7),
              width: Math.max(layout.barWidth * 0.8, 14),
              height: CHART_HEIGHT - 8,
            }}
          />
          {/* 고른 날 세로 띠 */}
          {selected !== null && (
            <div
              aria-hidden
              className="pointer-events-none absolute top-0 rounded-md bg-slate-400/15"
              style={{
                left: layout.xs[selected] - layout.barWidth / 2,
                width: layout.barWidth,
                height: CHART_HEIGHT,
              }}
            />
          )}
          {/* 지난 카드뉴스가 있던 날 ○ */}
          {Object.entries(layout.ringYs).map(([date, y]) => {
            const i = shown.findIndex((d) => d.date === date)
            return (
              <span
                key={date}
                aria-hidden
                className="pointer-events-none absolute size-4 rounded-full border-[2.6px] bg-white"
                style={{ left: layout.xs[i] - 8, top: y - RING_GAP - 8, borderColor: RING }}
              />
            )
          })}
          {/* 날짜 눈금: 5거래일마다 + 오늘 */}
          {shown.map((d, i) =>
            (shown.length - 1 - i) % 5 === 4 ? (
              <span
                key={d.date}
                aria-hidden
                className="text-faint pointer-events-none absolute -translate-x-1/2 text-[11px] font-bold tabular-nums"
                style={{ left: layout.xs[i], top: CHART_HEIGHT + 4 }}
              >
                {shortDate(d.date)}
              </span>
            ) : null,
          )}
          <span
            aria-hidden
            className="text-ink pointer-events-none absolute -translate-x-1/2 text-[11px] font-extrabold"
            style={{ left: layout.xs[layout.xs.length - 1], top: CHART_HEIGHT + 4 }}
          >
            오늘
          </span>
        </>
      )}

      {/* 손가락을 받는 막. 세로 스크롤(pan-y)은 브라우저에 맡긴다 */}
      <div
        ref={overlayRef}
        className="absolute inset-x-0 top-0 touch-pan-y select-none [-webkit-touch-callout:none]"
        style={{ height: CHART_HEIGHT + 22 }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={cancelPress}
        onContextMenu={(e) => e.preventDefault()}
      />

      {sel && layout && selected !== null && (
        <DayBubble
          candle={sel}
          prev={selPrev}
          note={notesByDate.get(sel.date) ?? null}
          market={chart.market}
          x={layout.xs[selected]}
          containerWidth={layout.width}
        />
      )}
    </div>
  )
}

/** ○ 를 고가에서 이만큼(px) 위에 띄운다 */
const RING_GAP = 14
const BUBBLE_WIDTH = 200

interface DayBubbleProps {
  candle: Candle
  prev: Candle | null
  note: StockChartNote | null
  market: StockChart['market']
  x: number
  containerWidth: number
}

/** 꾹 누른 날의 말풍선: "11/13 (목) 종가 191.20 ▲ +1.16%" + 이유 한두 문장 */
const DayBubble = ({ candle, prev, note, market, x, containerWidth }: DayBubbleProps) => {
  const chg = prev ? candle.close / prev.close - 1 : null
  // 고른 캔들을 가리지 않게 차트 오른쪽 절반이면 왼편에, 왼쪽 절반이면 오른편에 붙인다
  const gap = 14
  const wanted = x > containerWidth / 2 ? x - gap - BUBBLE_WIDTH : x + gap
  const left = Math.min(Math.max(wanted, 0), Math.max(containerWidth - BUBBLE_WIDTH, 0))

  return (
    <div
      role="status"
      className="border-line absolute bottom-7 z-10 rounded-2xl border-2 bg-white px-3.5 py-3 text-sm shadow-[0_12px_28px_rgba(43,51,68,0.14)]"
      style={{ left, width: BUBBLE_WIDTH }}
    >
      <p className="font-extrabold tabular-nums">
        {shortDate(candle.date)} ({weekday(candle.date)}) 종가 {formatPrice(candle.close, market)}
        {chg !== null && <ChangeText chg={chg} className="ml-1.5 inline" />}
      </p>
      <p className="text-sub mt-1 leading-snug font-medium break-keep">
        {note?.reason ?? '이날은 따로 정리한 이유가 없어요.'}
      </p>
      {note?.pastCardId && (
        <Link
          to={`/news/${note.pastCardId}`}
          className="bg-blue-soft text-blue-ink mt-2 flex min-h-9 items-center justify-between rounded-xl px-3 text-xs font-extrabold"
        >
          <span className="truncate pr-2">{note.pastCardTitle ?? '지난 카드뉴스'}</span>
          <span className="shrink-0">풀어보기 ›</span>
        </Link>
      )}
    </div>
  )
}

const ChangeText = ({ chg, className = '' }: { chg: number; className?: string }) => {
  const up = chg > 0
  const flat = chg === 0
  const color = flat ? 'text-sub' : up ? 'text-up' : 'text-down'
  return (
    <span className={`font-extrabold whitespace-nowrap tabular-nums ${color} ${className}`}>
      {flat ? '' : up ? '▲ ' : '▼ '}
      {up ? '+' : ''}
      {(chg * 100).toFixed(2)}%
    </span>
  )
}

/** n일 이동평균. 앞쪽 n-1일은 값이 없다 */
const movingAverage = (candles: Candle[], n: number) => {
  const out: { date: string; value: number }[] = []
  let sum = 0
  candles.forEach((c, i) => {
    sum += c.close
    if (i >= n) sum -= candles[i - n].close
    if (i >= n - 1) out.push({ date: c.date, value: Math.round((sum / n) * 100) / 100 })
  })
  return out
}

/** 화면 첫날의 전날 (앞쪽 여유분이 있으면) */
const prevOf = (candles: Candle[], candle: Candle | null) => {
  if (!candle) return null
  const i = candles.findIndex((c) => c.date === candle.date)
  return i > 0 ? candles[i - 1] : null
}

const formatPrice = (value: number, market: StockChart['market']) =>
  market === 'US' ? `$${value.toFixed(2)}` : `${Math.round(value).toLocaleString('ko-KR')}원`

/** '2026-11-13' → '11/13' */
const shortDate = (date: string) => {
  const [, month, day] = date.split('-').map(Number)
  return `${month}/${day}`
}

/** '2026-11-13' → '목' */
const weekday = (date: string) => '일월화수목금토'[new Date(`${date}T00:00:00Z`).getUTCDay()]
