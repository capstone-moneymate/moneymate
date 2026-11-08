import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
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
