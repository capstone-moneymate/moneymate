interface ProgressBarProps {
  done: number
  total: number
}

/** "N / total 학습" 진행률 */
export const ProgressBar = ({ done, total }: ProgressBarProps) => {
  const ratio = total === 0 ? 0 : Math.min(done / total, 1)

  return (
    <div className="flex items-center gap-3">
      <div
        className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={done}
      >
        <div
          className="bg-primary h-full rounded-full transition-all"
          style={{ width: `${ratio * 100}%` }}
        />
      </div>
      <span className="shrink-0 text-sm font-semibold text-slate-700">
        {done} / {total} 학습
      </span>
    </div>
  )
}
