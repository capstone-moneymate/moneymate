import { ChangeRate } from '@/components/ChangeRate'
import type { FilerChange } from '@/types/overlap'
import { CHANGE_TYPE_LABEL } from './labels'

/** 큰손 한 명의 13F 변화: "늘림 ▲ 10.00%", "새로 담음 ▲", "기록 없음" */
export const FilerChangeText = ({ change }: { change: FilerChange | undefined }) => {
  if (!change || !change.changeType) {
    return <span className="text-sm text-slate-400">기록 없음</span>
  }
  const label = CHANGE_TYPE_LABEL[change.changeType]
  switch (change.changeType) {
    case 'new':
      return <span className="text-up text-sm font-semibold">{label} ▲</span>
    case 'exit':
      return <span className="text-down text-sm font-semibold">{label} ▼</span>
    case 'unchanged':
      return <span className="text-sm text-slate-500">{label}</span>
    default:
      return (
        <span className="text-sm whitespace-nowrap">
          <span className="mr-1 text-slate-600">{label}</span>
          {change.chgPct === null ? null : (
            <ChangeRate value={change.chgPct} className="tabular-nums" />
          )}
        </span>
      )
  }
}

/** ETF 추세: 새로 담았으면 null 이라 "새로 담음 ▲" */
export const TrendText = ({ value }: { value: number | null }) => {
  if (value === null) {
    return <span className="text-up text-sm font-semibold">새로 담음 ▲</span>
  }
  return <ChangeRate value={value} className="text-sm tabular-nums" />
}
