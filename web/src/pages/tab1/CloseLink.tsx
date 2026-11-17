import { Link } from 'react-router'

/** 둥근 아이콘 버튼 색. light: 흰 화면(회색 원), onBlue: 파란 카드뉴스(반투명 흰 원) */
export type RoundTone = 'light' | 'onBlue'

const roundClass = (tone: RoundTone) =>
  `flex size-11 shrink-0 items-center justify-center rounded-full ${
    tone === 'onBlue' ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-700'
  }`

/** 오른쪽 위 닫기(×) → 뉴스 홈 */
export const CloseLink = ({ tone = 'light' }: { tone?: RoundTone }) => {
  return (
    <Link to="/" aria-label="닫고 뉴스 홈으로" className={roundClass(tone)}>
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden
      >
        <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
      </svg>
    </Link>
  )
}

/** 왼쪽 위 뒤로(‹) */
export const BackButton = ({ onClick, label }: { onClick: () => void; label: string }) => {
  return (
    <button type="button" onClick={onClick} aria-label={label} className={roundClass('light')}>
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden
      >
        <path d="M15 5l-7 7 7 7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  )
}
