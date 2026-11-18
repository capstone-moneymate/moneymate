import { getLoginId } from '@/lib/userId'

/**
 * 시작 화면(/welcome)을 지나갔는지. 로그인·가입하거나 "로그인 없이 둘러보기"를 누르면 표시한다.
 * 이 표시가 없으면 앱을 열 때 시작 화면으로 보낸다 (router.tsx 의 loader).
 */
const ENTERED_KEY = 'moneymate.entered'

export const hasEntered = (): boolean => {
  try {
    return localStorage.getItem(ENTERED_KEY) === '1' || getLoginId() !== null
  } catch {
    // 저장소를 못 쓰면 시작 화면을 매번 보여 주지 않는다
    return true
  }
}

export const markEntered = (): void => {
  try {
    localStorage.setItem(ENTERED_KEY, '1')
  } catch {
    // 저장소를 못 쓰면 표시만 안 된다
  }
}

/** 시작 화면 없이 바로 들어가도 되는 경로 (시작 화면 자신과 로그인 화면) */
export const ENTRY_FREE_PATHS = ['/welcome', '/login']
