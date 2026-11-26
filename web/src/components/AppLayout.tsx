import { Outlet, useLocation } from 'react-router'
import { BottomNav } from '@/components/BottomNav'
import { ENTRY_FREE_PATHS } from '@/lib/entry'

/**
 * 모바일 프레임 (UI 시안 app.html 의 .app). 폰에서는 화면 전체를 쓰고,
 * 넓은 화면에서는 가운데에 393×852 폰 크기로 보여준다.
 * 하단 탭은 뉴스 홈·13F·ETF·마이페이지에만 둔다. 시작·로그인 화면과
 * 카드뉴스·학습·결과(/news/…)·분석 자료 퀴즈(/lab/…)·복습 문제(/mypage/review)는 화면 전체를 쓴다 (아래에 고정 버튼이 있다).
 */
export const AppLayout = () => {
  const { pathname } = useLocation()
  const fullScreen =
    ENTRY_FREE_PATHS.includes(pathname) ||
    pathname.startsWith('/news/') ||
    pathname.startsWith('/lab/') ||
    pathname === '/mypage/review'
  return (
    <div className="flex min-h-dvh justify-center sm:items-center">
      <div className="flex h-dvh w-full flex-col overflow-hidden bg-white break-keep sm:h-[min(100dvh,852px)] sm:max-w-[393px] sm:rounded-[40px] sm:shadow-[0_30px_80px_rgba(43,51,68,0.18)]">
        <main className="min-h-0 flex-1 overflow-y-auto">
          <Outlet />
        </main>
        {!fullScreen && <BottomNav />}
      </div>
    </div>
  )
}
