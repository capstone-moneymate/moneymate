import { Outlet, useLocation } from 'react-router'
import { BottomNav } from '@/components/BottomNav'
import { ENTRY_FREE_PATHS } from '@/lib/entry'

/**
 * 모바일 390×844 프레임. 폰에서는 화면 전체를 쓰고,
 * 넓은 화면에서는 가운데에 폰 크기로 보여준다.
 * 시작 화면과 로그인 화면에는 하단 탭을 두지 않는다.
 */
export const AppLayout = () => {
  const { pathname } = useLocation()
  return (
    <div className="flex min-h-dvh justify-center bg-slate-200 sm:items-center">
      <div className="flex h-dvh w-full max-w-[390px] flex-col overflow-hidden break-keep bg-white sm:h-[844px] sm:rounded-3xl sm:shadow-xl">
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
        {!ENTRY_FREE_PATHS.includes(pathname) && <BottomNav />}
      </div>
    </div>
  )
}
