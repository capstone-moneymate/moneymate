import type { FilerChange } from '@/types/overlap'

/**
 * 탭2 이름·라벨 상수. 서버는 영어 상수와 코드만 내려 주고 한글은 여기서 바꾼다.
 * 안내·대체 문구는 notices.ts 에 모은다 (#101).
 */

/**
 * 큰손 4명 (worker/config.py FILERS 와 같은 키, 같은 순서).
 * 13F 는 법인 단위 기록이라 법인명(name)을 두고, 화면 시안(18~25)은 사람 이름(short)으로 보여 준다.
 */
export const FILERS = [
  { key: 'buffett', name: 'Berkshire Hathaway', person: '버핏의 회사', short: '워런 버핏' },
  { key: 'druckenmiller', name: 'Duquesne', person: '드러켄밀러의 회사', short: '드러켄밀러' },
  { key: 'thiel', name: 'Thiel Macro', person: '틸의 회사', short: '피터 틸' },
  { key: 'ackman', name: 'Pershing Square', person: '애크먼의 회사', short: '빌 애크먼' },
] as const

/** 액티브 ETF 이름 (docs/findings.md). 목록에 없는 코드는 코드 그대로 보여 준다 */
const ETF_NAMES: Record<string, { short: string; full: string }> = {
  '426030': { short: 'TIME', full: 'TIME 미국나스닥100액티브' },
  '0015B0': { short: 'KoAct', full: 'KoAct 미국나스닥성장기업액티브' },
}

export const etfShortName = (code: string) => ETF_NAMES[code]?.short ?? code

/** 시안 18·19 의 사람 이름 ("드러켄밀러 · 피터 틸 · 빌 애크먼") */
export const filerPersonName = (key: string) => FILERS.find((f) => f.key === key)?.short ?? key

/** '2026-09-30' → '9/30' (시안 표기) */
export const shortDate = (date: string) => {
  const [, month, day] = date.split('-').map(Number)
  return `${month}/${day}`
}

/** 분기 말 날짜 → '3분기' */
export const quarterOf = (date: string) => `${Math.ceil(Number(date.split('-')[1]) / 3)}분기`

/** 분기 말 날짜 → '7~9월' */
export const quarterMonths = (date: string) => {
  const month = Number(date.split('-')[1])
  return `${month - 2}~${month}월`
}

/** 소수 변화율 → '+6.0%' / '−5.4%' (digits 자리) */
export const signedPct = (value: number, digits = 1) =>
  `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value * 100).toFixed(digits)}%`

/**
 * 13F 에서 "늘림"으로 보는가. worker 의 big_direction(compute/overlap.py)과 같은 기준:
 * 새로 담았거나(new), 직전 분기 대비 +5%(config.INCREASE_THRESHOLD) 이상. 기준을 바꾸면 둘 다 고친다.
 */
export const INCREASE_THRESHOLD = 0.05
export const isBigUp = (f: FilerChange) =>
  f.changeType === 'new' || (f.chgPct !== null && f.chgPct >= INCREASE_THRESHOLD)

/** worker big_direction 의 "줄임": 모두 정리(exit)했거나 직전 분기 대비 −5% 이하 */
export const isBigDown = (f: FilerChange) =>
  f.changeType === 'exit' || (f.chgPct !== null && f.chgPct <= -INCREASE_THRESHOLD)

/**
 * 이번 분기 말에 들고 있는가 (탭2 메인 "겹치는 종목" 기준, #164). 방향과 상관없이 보유면 센다.
 * 모두 정리(exit)했으면 보유가 아니다. worker compute/overlap.py 의 is_held·co_held 와 같은 기준이라
 * 바꾸면 둘 다 고친다 (#172).
 */
export const isBigHeld = (f: FilerChange) => f.changeType !== null && f.changeType !== 'exit'

/** 메인 목록 라벨: 신규 / 늘림 / 줄임 / 유지 (늘림·줄임은 ±5% 기준, 판정은 worker 와 같다) */
export const bigChangeLabel = (f: FilerChange) =>
  f.changeType === 'new' ? '신규' : isBigUp(f) ? '늘림' : isBigDown(f) ? '줄임' : '유지'

/** 두 날짜(YYYY-MM-DD) 사이 일수 */
export const daysBetween = (from: string, to: string) =>
  Math.round((Date.parse(to) - Date.parse(from)) / 86_400_000)
