import type { ReactNode } from 'react'

interface StepFrameProps {
  /** 제목 위 작은 표시 (예: "퀴즈 1 / 2"). 단계 이름은 LearnPage 위쪽 STEP 줄에 있다 */
  badge?: string
  /** 큰 제목. 판단해보기처럼 제목을 내용 칸 안에 넣는 단계는 비운다 */
  heading?: string
  children: ReactNode
  /** 아래 고정 버튼 */
  buttonLabel: string
  buttonDisabled?: boolean
  onButton: () => void
}

/** 단계 화면 공통 틀: (배지) → 큰 제목 → 내용 → 아래 파란 버튼 (UI 시안 05~15) */
export const StepFrame = ({
  badge,
  heading,
  children,
  buttonLabel,
  buttonDisabled = false,
  onButton,
}: StepFrameProps) => {
  return (
    <div className="flex flex-1 flex-col px-5 pt-6 pb-5">
      {badge && (
        <span className="text-primary mb-3 self-start rounded-lg bg-blue-50 px-2.5 py-1 text-sm font-bold">
          {badge}
        </span>
      )}
      {heading && (
        <h2 className="mb-5 text-2xl leading-snug font-bold whitespace-pre-line text-slate-900">
          {heading}
        </h2>
      )}
      <div className="flex-1">{children}</div>
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
