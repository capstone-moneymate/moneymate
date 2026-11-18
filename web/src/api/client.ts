import axios from 'axios'
import { getLoginId, resetUserId } from '@/lib/userId'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

/**
 * 로그인이 풀린 채 계정 userId 로 부르면 서버가 401 을 준다 (서버 재시작, 7일 지남).
 * 새 익명 ID 로 돌리고 로그인 화면으로 보낸다. /api/auth/* 의 401 은 화면이 직접 다룬다.
 */
apiClient.interceptors.response.use(undefined, (error: unknown) => {
  if (
    axios.isAxiosError(error) &&
    error.response?.status === 401 &&
    !error.config?.url?.startsWith('/api/auth/') &&
    getLoginId()
  ) {
    resetUserId()
    window.location.assign('/login?expired=1')
  }
  return Promise.reject(error)
})

/**
 * 목 데이터로 돌릴지. 서버(Spring)가 develop 에 올라오기 전까지는 기본값이 목이다.
 * 실제 서버에 붙일 때 web/.env 에 VITE_USE_MOCK=false 를 넣는다.
 */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

/**
 * 하루 판단 채점 횟수를 다 썼을 때(429). 화면은 서버 문구를 그대로 보여 주고,
 * 채점 없이 결과 화면으로 넘어갈 수 있게 한다.
 */
export class DailyLimitError extends Error {}
