import type { ReactNode } from 'react'

interface StepFrameProps {
  /** 작은 파란 라벨 (예: "개념 학습") */
  label: string
  heading: string
  children: ReactNode
  /** 아래 고정 버튼 */
  buttonLabel: string
  buttonDisabled?: boolean
  onButton: () => void
}

/** 단계 화면 공통 틀: 라벨 → 큰 제목 → 내용 → 아래 파란 버튼 (UI 수정안 카드 넘김과 같은 모양) */
export const StepFrame = ({
  label,
  heading,
  children,
  buttonLabel,
  buttonDisabled = false,
  onButton,
}: StepFrameProps) => {
  return (
    <div className="flex flex-1 flex-col px-5 pt-4 pb-5">
      <p className="text-primary text-sm font-semibold">{label}</p>
      <h2 className="mt-2 text-xl leading-snug font-bold whitespace-pre-line text-slate-900">
        {heading}
      </h2>
      <div className="mt-5 flex-1">{children}</div>
      <button
        type="button"
        // 클릭 이벤트를 넘기지 않는다 (onNext(result?)에 이벤트가 결과로 들어가 점수가 틀어졌던 버그)
        onClick={() => onButton()}
        disabled={buttonDisabled}
        className="bg-primary mt-6 w-full rounded-2xl py-4 text-base font-bold text-white transition active:scale-[0.99] disabled:bg-slate-300"
      >
        {buttonLabel}
      </button>
    </div>
  )
}
