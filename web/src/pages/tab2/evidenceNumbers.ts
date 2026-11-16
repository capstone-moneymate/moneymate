import type { ReasonEvidence, StockReason } from '@/types/overlap'

/** 같은 자료를 알아보는 열쇠: C 가 붙인 번호가 있으면 그것, 없으면 링크 */
export const evidenceKey = (e: ReasonEvidence) => (e.no !== null ? `no:${e.no}` : `url:${e.url}`)

/**
 * 카드 ② 근거 번호. C 의 번호(no)는 근거 후보 20개에 붙인 것이라 [4], [11]처럼 띄엄띄엄이다.
 * 화면에서는 이유 순서대로 처음 나온 자료부터 1, 2, 3… 으로 다시 매기고, 같은 자료는 같은 번호를 준다.
 */
export const evidenceNumbers = (reasons: StockReason[]) => {
  const numbers = new Map<string, number>()
  for (const r of reasons) {
    for (const e of r.evidence) {
      const key = evidenceKey(e)
      if (!numbers.has(key)) numbers.set(key, numbers.size + 1)
    }
  }
  return numbers
}
