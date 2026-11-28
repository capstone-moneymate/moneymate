import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { authErrorMessage, useLogin, useSignup } from '@/api/auth'
import { Mate } from '@/components/Mate'
import { markEntered } from '@/lib/entry'

type Mode = 'login' | 'signup'

/** 서버 SignupRequest 와 같은 규칙. 서버도 다시 검사한다 */
const LOGIN_ID_RULE = /^[a-z0-9_]{4,20}$/
const MIN_PASSWORD = 8
const MAX_PASSWORD = 64

/** 회원가입 입력 검사. 문제가 없으면 null */
const validateSignup = (
  loginId: string,
  password: string,
  passwordCheck: string,
): string | null => {
  if (!LOGIN_ID_RULE.test(loginId)) return '아이디는 영문 소문자·숫자 4~20자로 써 주세요'
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
    <div className="flex min-h-full flex-col">
      {/* UI 시안 app.html 의 로그인·가입 화면: 위에 마스코트와 인사말, 아래에 입력 칸 */}
      <div className="px-5 pt-[calc(14px+env(safe-area-inset-top))] pb-1.5">
        <Link to="/welcome" className="text-sub inline-flex h-9 items-center text-sm font-bold">
          MONEYMATE 소개로
        </Link>
        <div className="mt-2.5 flex items-end gap-3">
          <Mate mood={mode === 'login' ? 'hi' : 'happy'} className="size-[84px] shrink-0" />
          <h1 className="font-display text-[28px] leading-tight">
            {mode === 'login' ? (
              <>
                다시 왔네요,
                <br />
                오늘 뉴스 볼까요
              </>
            ) : (
              <>
                하루 5분,
                <br />
                같이 시작해요
              </>
            )}
          </h1>
        </div>
      </div>

      <form onSubmit={onSubmit} className="flex-1 px-5 pt-4 pb-6" noValidate>
        <p className="text-sub mb-4 text-sm leading-relaxed font-medium">
          {mode === 'login'
            ? '로그인하면 다른 기기에서도 학습 기록을 이어 볼 수 있어요.'
            : '지금까지 이 기기에서 푼 기록이 새 계정으로 이어져요.'}
        </p>
        {params.get('expired') && (
          <p className="bg-mist mb-4 rounded-2xl px-4 py-3 text-sm font-semibold">
            로그인이 끝났어요. 다시 로그인해 주세요.
          </p>
        )}

        <Field
          label="아이디"
          value={loginId}
          onChange={setLoginIdInput}
          autoComplete="username"
          placeholder={mode === 'signup' ? '영문 소문자·숫자 4~20자' : '아이디를 입력하세요'}
        />
        <Field
          label="비밀번호"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          placeholder={mode === 'signup' ? '8자 이상' : '비밀번호를 입력하세요'}
        />
        {mode === 'signup' && (
          <Field
            label="비밀번호 확인"
            type="password"
            value={passwordCheck}
            onChange={setPasswordCheck}
            autoComplete="new-password"
            placeholder="한 번 더 입력하세요"
          />
        )}

        <p role="alert" className="text-no-ink mt-0.5 mb-2.5 min-h-[22px] text-[13.5px] font-bold">
          {message}
        </p>

        <button type="submit" disabled={pending || !loginId.trim() || !password} className="mm-btn">
          {pending ? '잠시만요' : mode === 'login' ? '로그인' : '가입하고 시작하기'}
        </button>

        <p className="text-sub mt-4 text-center text-[14.5px] font-semibold">
          {mode === 'login' ? '처음이신가요? ' : '이미 계정이 있나요? '}
          <button
            type="button"
            onClick={() => switchMode(mode === 'login' ? 'signup' : 'login')}
            className="text-blue-ink font-extrabold underline underline-offset-4"
          >
            {mode === 'login' ? '가입하기' : '로그인'}
          </button>
        </p>
        {mode === 'signup' && (
          <p className="text-faint mt-3.5 text-center text-[12.5px] leading-relaxed font-medium">
            머니메이트는 투자 권유가 아닌 학습용 서비스예요.
          </p>
        )}

        <button type="button" onClick={() => void navigate(-1)} className="mm-textbtn mt-3">
          나중에 할게요
        </button>
      </form>
    </div>
  )
}

type FieldProps = {
  label: string
  value: string
  onChange: (v: string) => void
  type?: 'text' | 'password'
  autoComplete: string
  placeholder: string
}

const Field = ({
  label,
  value,
  onChange,
  type = 'text',
  autoComplete,
  placeholder,
}: FieldProps) => (
  <label className="mm-field">
    <span>{label}</span>
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      autoComplete={autoComplete}
      autoCapitalize="none"
      spellCheck={false}
      placeholder={placeholder}
    />
  </label>
)
