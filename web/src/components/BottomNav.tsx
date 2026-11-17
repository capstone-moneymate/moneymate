import { NavLink, useLocation } from 'react-router'

const TABS = [
  { to: '/', label: '뉴스', icon: NewsIcon },
  { to: '/etf', label: '13F·ETF', icon: ChartIcon },
  { to: '/mypage', label: '마이페이지', icon: UserIcon },
]

/** 카드뉴스(/news/:id)는 화면 전체가 파랗다 (UI 시안 02~04) */
const BLUE_PAGE = /^\/news\/[^/]+$/

/** 하단 탭 3개. 카드뉴스·학습·결과(/news/…)에서도 뉴스 탭이 켜진다 */
export const BottomNav = () => {
  const { pathname } = useLocation()
  const blue = BLUE_PAGE.test(pathname)
  const inNews = pathname === '/' || pathname.startsWith('/news/')

  return (
    <nav
      className={`grid shrink-0 grid-cols-3 border-t pb-[env(safe-area-inset-bottom)] ${
        blue ? 'border-transparent bg-[#2f74e0]' : 'border-slate-200 bg-white'
      }`}
    >
      {TABS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) => {
            const active = to === '/' ? inNews : isActive
            const color = blue
              ? active
                ? 'font-semibold text-white'
                : 'text-white/70'
              : active
                ? 'text-primary font-semibold'
                : 'text-slate-500'
            return `flex flex-col items-center gap-1 py-2.5 text-xs ${color}`
          }}
        >
          <Icon />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}

function NewsIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5M9 13h6M9 17h6" />
    </svg>
  )
}

function ChartIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <path d="M6 20v-6M12 20V4M18 20v-10" strokeLinecap="round" />
    </svg>
  )
}

function UserIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" strokeLinecap="round" />
    </svg>
  )
}
