import { Link } from 'react-router'

/** 닫기(×) → 뉴스 홈(기본) 또는 to 로. 테두리 있는 둥근 버튼 (UI 시안 app.html 의 .l-top .close) */
export const CloseLink = ({
  to = '/',
  label = '닫고 뉴스 홈으로',
}: {
  to?: string
  label?: string
}) => {
  return (
    <Link to={to} aria-label={label} className="mm-round">
      <svg
        width="16"
        height="16"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
        aria-hidden
      >
        <path d="M4 4l12 12M16 4L4 16" />
      </svg>
    </Link>
  )
}

/** 뒤로(←) */
export const BackButton = ({ onClick, label }: { onClick: () => void; label: string }) => {
  return (
    <button type="button" onClick={onClick} aria-label={label} className="mm-round">
      <svg
        width="16"
        height="16"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        <path d="M11 4l-6 6 6 6M5 10h11" />
      </svg>
    </button>
  )
}
