const STORAGE_KEY = 'moneymate.userId'

/** 저장소를 못 쓸 때 이번 페이지 동안 쓰는 ID (호출할 때마다 바뀌지 않게) */
let sessionUserId: string | null = null

/**
 * UUID v4를 만든다.
 * crypto.randomUUID는 보안 연결(HTTPS·localhost)에서만 있어서, 폰에서 http://내부IP:5173 으로
 * 접속하면 없다. 그때는 어디서나 되는 crypto.getRandomValues로 같은 형식을 만든다.
 */
export const createUuid = (): string => {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()

  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40 // 버전 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80 // RFC 4122 변형
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

/**
 * 익명 사용자 ID. 첫 실행 때 UUID를 만들어 localStorage에 둔다.
 * 기기·브라우저에 묶이는 한계가 있다 (발표에서 명시).
 */
export const getUserId = (): string => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return saved
    const created = createUuid()
    localStorage.setItem(STORAGE_KEY, created)
    return created
  } catch {
    // 시크릿 모드 등으로 저장소를 못 쓰면 이번 페이지 동안만 쓰는 ID
    sessionUserId ??= createUuid()
    return sessionUserId
  }
}

/**
 * 로그인·회원가입 뒤 계정의 UUID 로 바꾼다. 기존 API 는 그대로 getUserId() 를 보내고,
 * 서버는 계정에 붙은 UUID 면 로그인 세션인지 확인한다 (docs/modules/auth_api.md).
 */
export const setUserId = (id: string): void => {
  sessionUserId = id
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    // 저장소를 못 쓰면 이번 페이지 동안만
  }
}

/** 로그아웃하거나 로그인이 풀렸을 때: 새 익명 ID 로 시작한다 (계정 UUID 를 익명으로 계속 쓰지 않게). */
export const resetUserId = (): string => {
  const created = createUuid()
  setUserId(created)
  setLoginId(null)
  return created
}

const LOGIN_KEY = 'moneymate.loginId'

/** 로그인한 아이디. 화면 표시와 "로그인이 살아 있는지 확인할지" 판단에만 쓴다. 진짜 확인은 서버 세션 */
export const getLoginId = (): string | null => {
  try {
    return localStorage.getItem(LOGIN_KEY)
  } catch {
    return null
  }
}

export const setLoginId = (loginId: string | null): void => {
  try {
    if (loginId) localStorage.setItem(LOGIN_KEY, loginId)
    else localStorage.removeItem(LOGIN_KEY)
  } catch {
    // 저장소를 못 쓰면 표시만 안 된다
  }
}
