import { Link, useNavigate } from 'react-router'
import { markEntered } from '@/lib/entry'

/**
 * 앱 시작 화면 (/welcome): 로그인하기 · 가입하기 · 로그인 없이 둘러보기.
 * 처음 열 때만 나온다. 둘러보기를 고르면 지금처럼 익명 ID 로 쓰고, 나중에 마이페이지에서 가입할 수 있다.
 */
export const WelcomePage = () => {
  const navigate = useNavigate()

  const browse = () => {
    markEntered()
    void navigate('/', { replace: true })
  }

  return (
    <div className="flex min-h-full flex-col bg-linear-to-b from-blue-50 via-white to-white px-6 pt-16 pb-10">
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <p className="text-primary text-sm font-semibold">뉴스로 배우는 경제의 연결 고리</p>
        <h1 className="text-primary mt-3 text-5xl font-extrabold tracking-tight">MoneyMate</h1>
        <p className="mt-5 text-base leading-relaxed font-medium text-slate-600">
          오늘의 뉴스에서 원인과 결과를 찾고
          <br />
          나만의 인과 지도를 쌓아 보세요
        </p>
      </div>

      <div className="mt-10 space-y-3">
        <Link
          to="/login?next=/"
          className="bg-primary block w-full rounded-full py-4 text-center text-lg font-bold text-white"
        >
          로그인하기
        </Link>
        <Link
          to="/login?mode=signup&next=/"
          className="block w-full rounded-full bg-slate-200 py-4 text-center text-lg font-bold text-slate-800"
        >
          가입하기
        </Link>
      </div>
      <button
        type="button"
        onClick={browse}
        className="border-primary text-primary mt-8 w-full rounded-full border-2 bg-white py-4 text-lg font-bold"
      >
        로그인 없이 둘러보기
      </button>
    </div>
  )
}
