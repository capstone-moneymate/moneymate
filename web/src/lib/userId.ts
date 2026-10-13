const STORAGE_KEY = 'moneymate.userId'

/**
 * 익명 사용자 ID. 첫 실행 때 UUID를 만들어 localStorage에 둔다.
 * 기기·브라우저에 묶이는 한계가 있다 (발표에서 명시).
 */
export const getUserId = (): string => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return saved
    const created = crypto.randomUUID()
    localStorage.setItem(STORAGE_KEY, created)
    return created
  } catch {
    // 시크릿 모드 등으로 저장소를 못 쓰면 이번 세션 동안만 쓰는 ID
    return crypto.randomUUID()
  }
}
