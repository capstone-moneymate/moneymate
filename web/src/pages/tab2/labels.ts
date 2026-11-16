import type { ChangeType, Direction } from '@/types/overlap'

/**
 * 탭2 이름·라벨 상수. 서버는 영어 상수와 코드만 내려 주고 한글은 여기서 바꾼다.
 * 안내·대체 문구는 notices.ts 에 모은다 (#101).
 */

/**
 * 큰손 4명 (worker/config.py FILERS 와 같은 키, 같은 순서).
 * 13F 는 법인 단위 기록이라 법인명 기준으로 쓰고 사람은 괄호로 덧붙인다 (docs/findings.md).
 */
export const FILERS = [
  { key: 'buffett', name: 'Berkshire Hathaway', person: '버핏의 회사' },
  { key: 'druckenmiller', name: 'Duquesne', person: '드러켄밀러의 회사' },
  { key: 'thiel', name: 'Thiel Macro', person: '틸의 회사' },
  { key: 'ackman', name: 'Pershing Square', person: '애크먼의 회사' },
] as const

/** 액티브 ETF 이름 (docs/findings.md). 목록에 없는 코드는 코드 그대로 보여 준다 */
const ETF_NAMES: Record<string, { short: string; full: string }> = {
  '426030': { short: 'TIME', full: 'TIME 미국나스닥100액티브' },
  '0015B0': { short: 'KoAct', full: 'KoAct 미국나스닥성장기업액티브' },
}

export const etfShortName = (code: string) => ETF_NAMES[code]?.short ?? code
export const etfFullName = (code: string) => ETF_NAMES[code]?.full ?? code

export const filerShortName = (key: string) => FILERS.find((f) => f.key === key)?.name ?? key

/** 13F 변화 종류 → 화면 문구. increase·decrease 는 변화율을 같이 보여 준다 */
export const CHANGE_TYPE_LABEL: Record<ChangeType, string> = {
  new: '새로 담음',
  increase: '늘림',
  decrease: '줄임',
  exit: '모두 정리',
  unchanged: '변화 없음',
}

/** 방향 비교 → 화면 문구 */
export const DIRECTION_LABEL: Record<Direction, string> = {
  same: '같은 방향',
  diff: '방향 다름',
  none: '비교 보류',
}

/** '2026-06-30' → '6월 30일' */
export const formatDate = (date: string) => {
  const [, month, day] = date.split('-').map(Number)
  return `${month}월 ${day}일`
}

/** 오늘(KST) 날짜 'YYYY-MM-DD' */
export const todayKst = () =>
  new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date())

/** 두 날짜(YYYY-MM-DD) 사이 일수 */
export const daysBetween = (from: string, to: string) =>
  Math.round((Date.parse(to) - Date.parse(from)) / 86_400_000)
