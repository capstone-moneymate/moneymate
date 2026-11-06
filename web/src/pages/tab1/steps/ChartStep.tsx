import { useEffect, useRef } from 'react'
import {
  ColorType,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  isBusinessDay,
  type Time,
} from 'lightweight-charts'
import { useChart } from '@/api/charts'
import type { ChartData } from '@/types/chart'

const COLOR = {
  primary: '#1b64da',
  bar: '#cbd5e1',
  text: '#64748b',
  grid: '#f1f5f9',
  border: '#e2e8f0',
}
const PRICE_VOLUME_HEIGHT = 240
const RSI_HEIGHT = 90

interface ChartStepProps {
  stepId: string
  ticker: string
}

/** 차트 읽기 단계의 차트. 보기·정답 확인은 QuizView 가 맡고, 여기는 데이터를 받아 그리기만 한다 */
export const ChartStep = ({ stepId, ticker }: ChartStepProps) => {
  const { data, isPending, isError } = useChart(stepId)

  if (isPending) return <ChartMessage text="차트를 불러오는 중…" />
  if (isError || !data || data.points.length === 0) {
    return <ChartMessage text="차트를 불러오지 못했어요. 보기는 그대로 고를 수 있어요." />
  }

  const hasRsi = data.points.some((p) => p.rsi != null)
  return (
    <figure className="mb-5">
      <PriceVolumeChart data={data} hasRsi={hasRsi} label={`${ticker} 가격·거래량 차트`} />
      <figcaption className="mt-2 text-xs text-slate-500">
        위: 종가 · 아래: 거래량{hasRsi && ' · 맨 아래: RSI'}
        {data.highlight && (
          <>
            {' · '}
            <span className="text-primary font-semibold">파란 막대: {data.highlight.label}</span>
          </>
        )}
        {/* TradingView Lightweight Charts™ Copyright 2023 TradingView, Inc. (라이선스의 출처 표기와 링크) */}
        <a
          href="https://www.tradingview.com/"
          target="_blank"
          rel="noreferrer"
          className="mt-1 block text-[11px] text-slate-400 underline"
        >
          차트: TradingView Lightweight Charts™
        </a>
      </figcaption>
    </figure>
  )
}

const ChartMessage = ({ text }: { text: string }) => {
  return (
    <div className="mb-5 flex h-40 items-center justify-center rounded-2xl bg-slate-50 px-4 text-center text-sm text-slate-500">
      {text}
    </div>
  )
}

interface PriceVolumeChartProps {
  data: ChartData
  hasRsi: boolean
  label: string
}

const PriceVolumeChart = ({ data, hasRsi, label }: PriceVolumeChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const height = PRICE_VOLUME_HEIGHT + (hasRsi ? RSI_HEIGHT : 0)

  useEffect(() => {
    if (!containerRef.current) return
    const chart = createChart(containerRef.current, {
      autoSize: true,
      // 손가락으로 차트를 밀어도 페이지가 스크롤되게 끄고, 전체 기간만 보여 준다
      handleScroll: false,
      handleScale: false,
      layout: {
        attributionLogo: false, // 로고가 거래량 막대를 가려서 figcaption 의 링크로 출처를 표기한다
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: COLOR.text,
        fontSize: 11,
      },
      localization: { locale: 'ko-KR', timeFormatter: formatDay },
      grid: { vertLines: { visible: false }, horzLines: { color: COLOR.grid } },
      rightPriceScale: { borderColor: COLOR.border },
      timeScale: {
        borderColor: COLOR.border,
        fixLeftEdge: true,
        fixRightEdge: true,
        tickMarkFormatter: formatDay,
      },
    })

    const line = { lastValueVisible: false, priceLineVisible: false, lineWidth: 2 } as const
    chart
      .addSeries(LineSeries, { ...line, color: COLOR.primary })
      .setData(data.points.map((p) => ({ time: p.date, value: p.close })))
    chart
      .addSeries(
        HistogramSeries,
        { lastValueVisible: false, priceLineVisible: false, priceFormat: { type: 'volume' } },
        1,
      )
      .setData(
        data.points.map((p) => ({
          time: p.date,
          value: p.volume,
          color: p.date === data.highlight?.date ? COLOR.primary : COLOR.bar,
        })),
      )

    if (hasRsi) {
      const rsi = chart.addSeries(
        LineSeries,
        {
          ...line,
          color: COLOR.text,
          lineWidth: 1,
          // 0~100 으로 고정해 70·30 기준선이 항상 보이게 한다
          autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }),
        },
        2,
      )
      rsi.setData(
        data.points.flatMap((p) => (p.rsi == null ? [] : [{ time: p.date, value: p.rsi }])),
      )
      for (const price of [70, 30]) {
        rsi.createPriceLine({
          price,
          color: COLOR.bar,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
        })
      }
    }

    chart.timeScale().fitContent()
    return () => chart.remove()
  }, [data, hasRsi])

  return <div ref={containerRef} role="img" aria-label={label} style={{ height }} />
}

/** 축·십자선의 날짜를 10/22 모양으로 */
const formatDay = (time: Time) => {
  if (typeof time === 'number') return ''
  const day = isBusinessDay(time) ? time : parseDay(time)
  return `${day.month}/${day.day}`
}

const parseDay = (date: string) => {
  const [, month, day] = date.split('-').map(Number)
  return { month, day }
}
