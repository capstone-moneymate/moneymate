import { Link } from 'react-router'
import { useLogout, useMe } from '@/api/auth'

/** 마이페이지 맨 위 계정 줄: 로그인했으면 아이디와 로그아웃, 아니면 로그인·회원가입 안내 */
export const AccountBar = () => {
  const me = useMe()
  const logout = useLogout()

  if (me.isPending) return null

  if (me.data) {
    return (
      <div className="mb-4 flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3 text-sm">
        <span className="text-slate-700">
          <span className="font-bold text-slate-900">{me.data.loginId}</span> 님
        </span>
        <button
          type="button"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          className="font-semibold text-slate-500"
        >
          로그아웃
        </button>
      </div>
    )
  }

  return (
    <div className="mb-4 rounded-2xl bg-slate-50 px-4 py-3 text-sm">
      <p className="leading-relaxed text-slate-700">
        로그인하면 다른 기기에서도 학습 기록을 이어 볼 수 있어요.
      </p>
      <div className="mt-2 flex gap-4 font-semibold">
        <Link to="/login?next=/mypage" className="text-blue-ink">
          로그인
        </Link>
        <Link to="/login?mode=signup&next=/mypage" className="text-blue-ink">
          회원가입
        </Link>
      </div>
    </div>
  )
}
