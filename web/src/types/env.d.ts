interface ImportMetaEnv {
  /** 백엔드 API 서버 주소 (예: http://localhost:8080) */
  readonly VITE_API_BASE_URL: string
  /** 'false' 면 실제 서버를 부르고, 그 밖에는 목 데이터를 쓴다 */
  readonly VITE_USE_MOCK?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
