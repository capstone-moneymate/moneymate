export type MateMood = 'smile' | 'hi' | 'think' | 'happy' | 'wink' | 'wow'

const INK = '#2B3344'

const OPEN_EYES = (
  <>
    <ellipse cx="76" cy="88" rx="17" ry="21" fill="#fff" stroke={INK} strokeWidth="5" />
    <ellipse cx="124" cy="88" rx="17" ry="21" fill="#fff" stroke={INK} strokeWidth="5" />
  </>
)
const SMILE = (
  <path d="M82 128q18 17 36 0" fill="none" stroke={INK} strokeWidth="6" strokeLinecap="round" />
)
const CHEEKS = (
  <>
    <circle cx="50" cy="118" r="11" fill="#FFB4C0" opacity=".85" />
    <circle cx="150" cy="118" r="11" fill="#FFB4C0" opacity=".85" />
  </>
)

/**
 * 마스코트 '메이트' (UI 시안 app.html 의 mate()). 노란 동그란 얼굴이고 mood 로 표정만 바꾼다.
 * 장식이라 화면 읽기 프로그램에는 숨긴다(aria-hidden). 크기는 부모나 className 으로 준다.
 * smile: 기본(눈 깜빡임) · hi: 손 흔들기 · think: 생각 중 · happy: 웃음 · wink: 윙크 · wow: 놀람
 */
export const Mate = ({ mood = 'smile', className }: { mood?: MateMood; className?: string }) => (
  <svg viewBox="-10 -10 232 220" aria-hidden className={className}>
    {mood === 'think' && (
      <>
        <circle cx="176" cy="30" r="7" fill="#fff" stroke={INK} strokeWidth="4" />
        <circle cx="194" cy="10" r="4" fill="#fff" stroke={INK} strokeWidth="3.5" />
      </>
    )}
    {mood === 'hi' && (
      <>
        <path
          d="M178 98c18-10 22-32 15-50"
          fill="none"
          stroke={INK}
          strokeWidth="6"
          strokeLinecap="round"
        />
        <path
          d="M176 30l-6-12M194 30l4-13M206 46l12-6"
          fill="none"
          stroke={INK}
          strokeWidth="4"
          strokeLinecap="round"
        />
      </>
    )}
    <circle cx="100" cy="100" r="86" fill="#FFC94D" stroke={INK} strokeWidth="6" />
    <circle
      cx="100"
      cy="100"
      r="70"
      fill="none"
      stroke={INK}
      strokeWidth="3"
      strokeDasharray="2 9"
      strokeLinecap="round"
      opacity=".3"
    />
    {(mood === 'happy' || mood === 'wink') && CHEEKS}
    <Face mood={mood} />
  </svg>
)

const Face = ({ mood }: { mood: MateMood }) => {
  switch (mood) {
    case 'think':
      return (
        <>
          {OPEN_EYES}
          <circle cx="70" cy="82" r="8" fill={INK} />
          <circle cx="118" cy="82" r="8" fill={INK} />
          <path d="M88 134h22" fill="none" stroke={INK} strokeWidth="6" strokeLinecap="round" />
        </>
      )
    case 'happy':
      return (
        <>
          <path
            d="M60 92q16-18 32 0M108 92q16-18 32 0"
            fill="none"
            stroke={INK}
            strokeWidth="6"
            strokeLinecap="round"
          />
          <path
            d="M80 124q20 24 40 0z"
            fill="#fff"
            stroke={INK}
            strokeWidth="6"
            strokeLinejoin="round"
          />
        </>
      )
    case 'wink':
      return (
        <>
          <ellipse cx="76" cy="88" rx="17" ry="21" fill="#fff" stroke={INK} strokeWidth="5" />
          <circle cx="80" cy="92" r="8" fill={INK} />
          <path
            d="M108 92q16-18 32 0"
            fill="none"
            stroke={INK}
            strokeWidth="6"
            strokeLinecap="round"
          />
          {SMILE}
        </>
      )
    case 'wow':
      return (
        <>
          {OPEN_EYES}
          <circle cx="76" cy="90" r="8" fill={INK} />
          <circle cx="124" cy="90" r="8" fill={INK} />
          <ellipse cx="100" cy="136" rx="9" ry="11" fill="#fff" stroke={INK} strokeWidth="5.5" />
        </>
      )
    default:
      return (
        <>
          <g className="mm-eye">
            {OPEN_EYES}
            <circle cx="80" cy="92" r="8" fill={INK} />
            <circle cx="128" cy="92" r="8" fill={INK} />
          </g>
          {SMILE}
        </>
      )
  }
}
