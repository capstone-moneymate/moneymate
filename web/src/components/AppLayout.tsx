import { Outlet } from 'react-router'
import { BottomNav } from '@/components/BottomNav'

/**
 * 모바일 390×844 프레임. 폰에서는 화면 전체를 쓰고,
 * 넓은 화면에서는 가운데에 폰 크기로 보여준다.
 */
export const AppLayout = () => {
  return (
    <div className="flex min-h-dvh justify-center bg-slate-200 sm:items-center">
      <div className="flex h-dvh w-full max-w-[390px] flex-col overflow-hidden bg-white sm:h-[844px] sm:rounded-3xl sm:shadow-xl">
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
        <BottomNav />
      </div>
    </div>
  )
}
