interface ChangeRateProps {
  /** 소수 변화율 (0.05 = +5%) */
  value: number
  className?: string
}

/** ▲▼ 변화율 표시. 늘림·상승은 빨강 ▲, 줄임·하락은 파랑 ▼ */
export const ChangeRate = ({ value, className = '' }: ChangeRateProps) => {
  const percent = `${Math.abs(value * 100).toFixed(2)}%`

  if (value > 0) {
    return <span className={`text-up font-semibold ${className}`}>▲ {percent}</span>
  }
  if (value < 0) {
    return <span className={`text-down font-semibold ${className}`}>▼ {percent}</span>
  }
  return <span className={`font-semibold text-slate-500 ${className}`}>- {percent}</span>
}
