import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { apiClient, USE_MOCK } from '@/api/client'
import { getLoginId, getUserId, resetUserId, setLoginId, setUserId } from '@/lib/userId'

/**
 * 회원가입·로그인 API (C, server auth 패키지, docs/modules/auth_api.md).
 * 로그인하면 서버가 세션 쿠키를 주고, 웹은 계정의 userId 를 localStorage 에 넣어 기존 API 에 그대로 보낸다.
 * - POST /api/auth/signup {userId, loginId, password}: 지금 익명 UUID 에 계정을 붙인다 (기록이 이어진다)
 * - POST /api/auth/login {loginId, password}
 * - POST /api/auth/logout
 * - GET  /api/auth/me: 로그인이 살아 있는지
 */
export type Me = { userId: string; loginId: string }

export const ME_KEY = ['auth', 'me'] as const

/** 서버가 보낸 message (없으면 기본 문구) */
export const authErrorMessage = (error: unknown): string => {
  if (isAxiosError<{ message?: string }>(error) && error.response?.data?.message) {
    return error.response.data.message
  }
  return '잠시 뒤 다시 시도해 주세요'
}

/** 로그인한 계정. 로그인 표시가 없으면 서버에 묻지 않고 null. 세션이 끝났으면 새 익명 ID 로 돌린다. */
const fetchMe = async (): Promise<Me | null> => {
  const loginId = getLoginId()
  if (!loginId) return null
  if (USE_MOCK) return { userId: getUserId(), loginId }
  try {
    const { data } = await apiClient.get<Me>('/api/auth/me')
    return data
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 401) {
      resetUserId()
      return null
    }
    throw error
  }
}

export const useMe = () => {
  return useQuery({ queryKey: ME_KEY, queryFn: fetchMe, staleTime: Infinity, retry: false })
}

type Credentials = { loginId: string; password: string }

/** 로그인·가입 성공 뒤 공통: 계정 UUID 로 바꾸고 모든 화면 데이터를 다시 읽는다 */
const useOnSignedIn = () => {
  const queryClient = useQueryClient()
  return (me: Me) => {
    setUserId(me.userId)
    setLoginId(me.loginId)
    queryClient.setQueryData(ME_KEY, me)
    void queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== ME_KEY[0] })
  }
}

export const useSignup = () => {
  const onSignedIn = useOnSignedIn()
  return useMutation({
    mutationFn: async (c: Credentials): Promise<Me> => {
      if (USE_MOCK) return { userId: getUserId(), loginId: c.loginId }
      const { data } = await apiClient.post<Me>('/api/auth/signup', { userId: getUserId(), ...c })
      return data
    },
    onSuccess: onSignedIn,
  })
}

export const useLogin = () => {
  const onSignedIn = useOnSignedIn()
  return useMutation({
    mutationFn: async (c: Credentials): Promise<Me> => {
      if (USE_MOCK) return { userId: getUserId(), loginId: c.loginId }
      const { data } = await apiClient.post<Me>('/api/auth/login', c)
      return data
    },
    onSuccess: onSignedIn,
  })
}

export const useLogout = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      if (!USE_MOCK) await apiClient.post('/api/auth/logout')
    },
    // 서버 요청이 실패해도 이 브라우저에서는 로그아웃한다
    onSettled: () => {
      resetUserId()
      queryClient.setQueryData(ME_KEY, null)
      void queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== ME_KEY[0] })
    },
  })
}
