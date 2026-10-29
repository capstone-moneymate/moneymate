import { Link } from 'react-router'

/** 오른쪽 위 닫기(×) → 뉴스 홈 */
export const CloseLink = () => {
  return (
    <Link
      to="/"
      aria-label="닫고 뉴스 홈으로"
      className="flex size-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-600"
    >
      <svg
        width="16"
        height="16"
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
