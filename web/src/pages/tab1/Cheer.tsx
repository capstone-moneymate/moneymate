import { useEffect, useState } from 'react'

/** 축하 화면이 떠 있는 시간과, 사라지는 데 걸리는 시간 (ms). design.css 의 .mm-cheer 애니메이션과 맞춘다 */
const SHOW_MS = 1500
const FADE_MS = 380

/** 흩어진 아이콘 한 개의 자리·기울기·늦춤 */
const spot = (x: number, y: number, r: number, d: number, s?: number) =>
  ({
    '--x': `${x}%`,
    '--y': `${y}%`,
    '--r': `${r}deg`,
    '--d': `${d}s`,
    ...(s ? { '--s': `${s}px` } : {}),
  }) as React.CSSProperties

const CANDLE = (
  <>
    <path d="M11 3v5M11 22v7M21 6v6M21 20v6" />
    <rect x="7" y="8" width="8" height="14" rx="2" />
    <rect x="17" y="12" width="8" height="8" rx="2" />
  </>
)
const COIN = (
  <>
    <circle cx="16" cy="16" r="11" />
    <path d="M10.5 12l2.6 8 2.9-7 2.9 7 2.6-8M10 15.5h12" />
  </>
)
const UP = <path d="M4 23l8-8 5 5 10-11M20 9h7v7" />
const CARD = (
  <>
    <rect x="6" y="4" width="20" height="24" rx="4" />
    <path d="M11 11h10M11 16h10M11 21h6" />
  </>
)

const ICONS = [
  { icon: CANDLE, style: spot(10, 10, -14, 0.05) },
  { icon: COIN, style: spot(76, 8, 12, 0.2, 34) },
  { icon: UP, style: spot(82, 27, -10, 0.1) },
  { icon: CARD, style: spot(14, 28, 16, 0.3, 26) },
  { icon: UP, style: spot(8, 68, 10, 0.25, 32) },
  { icon: CARD, style: spot(80, 70, -18, 0.35, 26) },
  { icon: COIN, style: spot(28, 84, -8, 0.15, 34) },
  { icon: CANDLE, style: spot(62, 86, 14, 0.28) },
]

/**
 * 학습을 끝내고 결과 화면에 들어올 때 잠깐 덮는 축하 화면 (UI 시안 app.html 의 .cheer): 파란 바탕에 "잘했어요!".
 * 1.5초 보여 주고 흐려지며 사라진다. 움직임 줄이기를 켠 기기에서는 아예 띄우지 않는다.
 * 부모가 position: relative 여야 그 칸을 덮는다.
 */
export const Cheer = () => {
  const [phase, setPhase] = useState<'on' | 'bye' | 'gone'>(() =>
    window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'gone' : 'on',
  )

  useEffect(() => {
    if (phase === 'gone') return
    const timer = window.setTimeout(
      () => setPhase(phase === 'on' ? 'bye' : 'gone'),
      phase === 'on' ? SHOW_MS : FADE_MS,
    )
    return () => window.clearTimeout(timer)
  }, [phase])

  if (phase === 'gone') return null
  return (
    <div className={`mm-cheer ${phase === 'bye' ? 'bye' : ''}`} aria-hidden>
      <div className="ic">
        {ICONS.map(({ icon, style }, i) => (
          <svg key={i} viewBox="0 0 32 32" style={style}>
            {icon}
          </svg>
        ))}
      </div>
      <svg className="rb" viewBox="0 0 390 844" preserveAspectRatio="xMidYMid slice">
        <path className="r1" pathLength="1" d="M-80 250 C 80 150, 250 240, 470 60" />
        <path className="r2" pathLength="1" d="M-70 760 C 110 640, 270 760, 470 590" />
      </svg>
      <h2>잘했어요!</h2>
    </div>
  )
}
