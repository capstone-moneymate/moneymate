import type { ReactNode } from 'react'
import { signedPct } from './labels'

/** 종목 상세 카드 ①②③ 공통 부품 (시안 19~25) */

/** "1 · 무엇이 바뀌었나요?" 같은 카드 번호 줄 */
export const CardLabel = ({ no, children }: { no: number; children: ReactNode }) => (
  <p className="text-primary text-[15px] font-bold">
    {no} · {children}
  </p>
)

/** 카드 큰 제목 (줄바꿈 \n 유지) */
export const CardTitle = ({ children }: { children: ReactNode }) => (
  <h2 className="mt-3 text-[26px] leading-snug font-bold whitespace-pre-line text-slate-900">
    {children}
  </h2>
)

/** ▲ +24% / ▼ −5.4%. 소수 변화율을 받는다. text 를 주면 숫자 대신 그 글자 (예: 신규) */
export const Rate = ({
  value,
  digits = 0,
  text,
}: {
  value: number
  digits?: number
  text?: string
}) => (
  <span
    className={`font-bold tabular-nums ${value > 0 ? 'text-up' : value < 0 ? 'text-down' : 'text-slate-500'}`}
  >
    {value > 0 ? '▲ ' : value < 0 ? '▼ ' : ''}
    {text ?? signedPct(value, digits)}
  </span>
)
