import { NavLink } from 'react-router'

/**
 * 탭2(13F·ETF)를 화면에 보일지. false면 하단 탭과 결과 화면의 탭2 이동 버튼을 숨긴다.
 * 탭2 코드와 /etf 경로는 그대로 남아 있어 true로 바꾸면 바로 되살아난다.
 */
export const SHOW_TAB2 = false

const TABS = [
  { to: '/', label: '뉴스', icon: NewsIcon },
  { to: '/lab', label: '분석 자료', icon: LabIcon },
  ...(SHOW_TAB2 ? [{ to: '/etf', label: '13F·ETF', icon: ChartIcon }] : []),
  { to: '/mypage', label: '마이페이지', icon: UserIcon },
]

/** 하단 탭: 뉴스 · 분석 자료 · (탭2를 켜면 13F·ETF) · 마이페이지. 켜진 탭은 연한 파란 칸 (UI 시안 app.html 의 .tabs) */
export const BottomNav = () => {
  return (
    <nav className="mm-tabs" aria-label="주요 메뉴">
      {TABS.map(({ to, label, icon: Icon }) => (
        <NavLink key={to} to={to} end={to === '/'}>
          <Icon />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}

function NewsIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M7 3h7l4 4v14H7z" />
      <path d="M10 12h5M10 16h5" />
    </svg>
  )
}

function LabIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.6 9.4a2.5 2.5 0 1 1 3.8 2.1c-.9.6-1.4 1.1-1.4 2.1M12 17.2v.1" />
    </svg>
  )
}

function ChartIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden>
      <path d="M6 20v-6M12 20V4M18 20v-10" />
    </svg>
  )
}

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c1-4.500 4-6 8-6s7 1.500 8 6" />
    </svg>
  )
}
