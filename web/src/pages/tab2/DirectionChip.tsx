import type { Direction } from '@/types/overlap'
import { DIRECTION_LABEL } from './labels'

const STYLE: Record<Direction, string> = {
  same: 'bg-emerald-50 text-emerald-700',
  diff: 'bg-amber-50 text-amber-700',
  none: 'bg-slate-100 text-slate-500',
}

/** 방향 비교 칩. count 를 주면 "같은 방향 2" */
export const DirectionChip = ({ direction, count }: { direction: Direction; count?: number }) => {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${STYLE[direction]}`}
    >
      {DIRECTION_LABEL[direction]}
      {count !== undefined && <span className="ml-1 tabular-nums">{count}</span>}
    </span>
  )
}
