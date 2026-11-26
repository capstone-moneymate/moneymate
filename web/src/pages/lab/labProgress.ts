import { getUserId } from '@/lib/userId'

/** 자료 하나의 진행: 시작함 / 풀었음(ok = 맞혔는지) */
export interface LabRecord {
  st: 'started' | 'done'
  ok?: boolean
}

export type LabProgress = Record<string, LabRecord>

/**
 * 분석 자료 탭의 진행 기록. 서버 API 가 없어서 이 기기에만 저장한다 (localStorage, 사용자 ID 별).
 * 저장을 못 하는 환경(사생활 보호 모드 등)에서는 화면을 떠나면 기록이 사라진다.
 */
const key = () => `mm:lab:${getUserId()}`

export const loadLab = (): LabProgress => {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(key()) ?? '{}')
    return parsed && typeof parsed === 'object' ? (parsed as LabProgress) : {}
  } catch {
    return {}
  }
}

/** 한 건을 고쳐 저장하고, 고친 전체 기록을 돌려준다 */
export const saveLab = (id: string, record: LabRecord): LabProgress => {
  const next = { ...loadLab(), [id]: record }
  try {
    localStorage.setItem(key(), JSON.stringify(next))
  } catch {
    // 저장 못 해도 화면에서는 진행된 상태로 보인다
  }
  return next
}

export const labStatus = (progress: LabProgress, id: string): 'new' | 'started' | 'done' =>
  progress[id]?.st ?? 'new'
