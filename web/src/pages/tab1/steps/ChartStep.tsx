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
import type { ChartData } from '@/types/chart'

const COLOR = {
  primary: '#3b8dff',
  bar: '#c6ceda',
  text: '#6b7688',
  grid: '#f3f6fa',
  border: '#e3e8ef',
}
const PRICE_VOLUME_HEIGHT = 240
const RSI_HEIGHT = 90

interface ChartStepProps {
  /** 카드 API 가 단계와 함께 내려 준 값 (steps.content.chart). 이 기능(#82) 전에 만든 카드에는 없다 */
  chart?: ChartData
  ticker: string
}

/** 차트 읽기 단계의 차트. 보기·정답 확인은 QuizView 가 맡고, 여기는 받은 데이터를 그리기만 한다 */
export const ChartStep = ({ chart: data, ticker }: ChartStepProps) => {
  if (!data || data.points.length === 0) {
    return <ChartMessage text="이 문제는 차트가 없어요. 보기는 그대로 고를 수 있어요." />
  }

  const hasRsi = data.points.some((p) => p.rsi != null)
  return (
    <figure className="mm-box mb-3.5 px-2 pt-3 pb-2.5">
      <PriceVolumeChart data={data} hasRsi={hasRsi} label={`${ticker} 가격·거래량 차트`} />
      <figcaption className="text-sub mt-2 px-1.5 text-xs font-semibold">
        위: 종가 · 아래: 거래량{hasRsi && ' · 맨 아래: RSI'}
        {data.highlight && (
          <>
            {' · '}
            <span className="text-blue-ink font-extrabold">파란 막대: {data.highlight.label}</span>
          </>
        )}
      </figcaption>
    </figure>
  )
}

const ChartMessage = ({ text }: { text: string }) => {
  return (
    <div className="bg-mist text-sub mb-3.5 flex h-40 items-center justify-center rounded-2xl px-4 text-center text-sm font-semibold">
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
        attributionLogo: false, // 출처 표기는 마이페이지 오픈소스 라이선스(components/OpenSourceNotice)에 모았다
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
