import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { authErrorMessage, useLogin, useSignup } from '@/api/auth'
import { markEntered } from '@/lib/entry'

type Mode = 'login' | 'signup'

/** 서버 SignupRequest 와 같은 규칙. 서버도 다시 검사한다 */
const LOGIN_ID_RULE = /^[a-z0-9_]{4,20}$/
const MIN_PASSWORD = 8
const MAX_PASSWORD = 64

/** 회원가입 입력 검사. 문제가 없으면 null */
const validateSignup = (loginId: string, password: string, passwordCheck: string): string | null => {
  if (!LOGIN_ID_RULE.test(loginId)) return '아이디는 영문 소문자·숫자·_ 4~20자로 써 주세요'
  if (password.length < MIN_PASSWORD || password.length > MAX_PASSWORD)
    return '비밀번호는 8~64자로 써 주세요'
  if (password !== passwordCheck) return '비밀번호가 서로 달라요'
  return null
}

/** 성공 뒤 갈 곳. 앱 안 경로(/로 시작, //로 시작하지 않음)만 받고 아니면 뉴스 홈 */
const safeNext = (next: string | null): string =>
  next && next.startsWith('/') && !next.startsWith('//') ? next : '/'

/**
 * 로그인·회원가입 화면 (/login). 회원가입하면 지금 브라우저에서 쌓은 학습 기록이 계정으로 이어진다.
 * 성공하면 ?next= 경로(시작 화면에서 오면 뉴스 홈, 마이페이지에서 오면 마이페이지)로 간다.
 */
export const LoginPage = () => {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [mode, setMode] = useState<Mode>(params.get('mode') === 'signup' ? 'signup' : 'login')
  const nextPath = safeNext(params.get('next'))
  const [loginId, setLoginIdInput] = useState('')
  const [password, setPassword] = useState('')
  const [passwordCheck, setPasswordCheck] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const login = useLogin()
  const signup = useSignup()
  const pending = login.isPending || signup.isPending
  const serverError = mode === 'login' ? login.error : signup.error

  const switchMode = (next: Mode) => {
    setMode(next)
    setFormError(null)
    login.reset()
    signup.reset()
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    const id = loginId.trim()
    const error = mode === 'signup' ? validateSignup(id, password, passwordCheck) : null
    setFormError(error)
    if (error) return
    const onSuccess = () => {
      markEntered()
      void navigate(nextPath, { replace: true })
    }
    if (mode === 'login') login.mutate({ loginId: id, password }, { onSuccess })
    else signup.mutate({ loginId: id, password }, { onSuccess })
  }

  const message = formError ?? (serverError ? authErrorMessage(serverError) : null)

  return (
    <div className="min-h-full px-6 pt-10 pb-8">
      <h1 className="text-2xl font-bold text-slate-900">
        {mode === 'login' ? '로그인' : '회원가입'}
      </h1>
      <p className="mt-2 text-sm leading-relaxed text-slate-500">
        {mode === 'login'
          ? '로그인하면 다른 기기에서도 학습 기록을 이어 볼 수 있어요.'
          : '지금까지 이 기기에서 푼 기록이 새 계정으로 이어져요.'}
      </p>
      {params.get('expired') && (
        <p className="mt-4 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
          로그인이 끝났어요. 다시 로그인해 주세요.
        </p>
      )}

      <div className="mt-6 grid grid-cols-2 rounded-2xl bg-slate-100 p-1 text-sm font-semibold">
        {(['login', 'signup'] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => switchMode(m)}
            aria-pressed={mode === m}
            className={`rounded-xl py-2.5 ${mode === m ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
          >
            {m === 'login' ? '로그인' : '회원가입'}
          </button>
        ))}
      </div>

      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        <Field
          label="아이디"
          value={loginId}
          onChange={setLoginIdInput}
          autoComplete="username"
          hint={mode === 'signup' ? '영문 소문자·숫자·_ 4~20자' : undefined}
        />
        <Field
          label="비밀번호"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          hint={mode === 'signup' ? '8자 이상' : undefined}
        />
        {mode === 'signup' && (
          <Field
            label="비밀번호 확인"
            type="password"
            value={passwordCheck}
            onChange={setPasswordCheck}
            autoComplete="new-password"
          />
        )}

        {message && (
          <p role="alert" className="text-up text-sm">
            {message}
          </p>
        )}

        <button
          type="submit"
          disabled={pending || !loginId.trim() || !password}
          className="bg-primary w-full rounded-2xl py-4 font-bold text-white disabled:opacity-40"
        >
          {pending ? '잠시만요' : mode === 'login' ? '로그인' : '가입하고 시작하기'}
        </button>
      </form>

      <button
        type="button"
        onClick={() => void navigate(-1)}
        className="mt-4 w-full py-2 text-sm text-slate-500"
      >
        나중에 할게요
      </button>
    </div>
  )
}

type FieldProps = {
  label: string
  value: string
  onChange: (v: string) => void
  type?: 'text' | 'password'
  autoComplete: string
  hint?: string
}

const Field = ({ label, value, onChange, type = 'text', autoComplete, hint }: FieldProps) => (
  <label className="block">
    <span className="text-sm font-semibold text-slate-700">{label}</span>
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      autoComplete={autoComplete}
      autoCapitalize="none"
      spellCheck={false}
      className="focus:ring-primary mt-2 w-full rounded-2xl bg-slate-100 px-4 py-3.5 outline-none focus:ring-2"
    />
    {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
  </label>
)
