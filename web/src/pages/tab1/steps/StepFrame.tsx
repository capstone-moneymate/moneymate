import type { ReactNode } from 'react'
import type { Confidence } from '@/types/card'

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
  /**
   * 있으면 아래 버튼 자리에 [헷갈려요] [확실해요]를 대신 보여 준다 (답을 고른 뒤, 정답을 보기 전).
   * 누르면 그 확신과 함께 답을 낸다. 누르는 횟수는 [정답 확인] 하나일 때와 같다
   */
  confidence?: ConfidenceProps
}

interface ConfidenceProps {
  disabled: boolean
  onPick: (confidence: Confidence) => void
}

/** 단계 화면 공통 틀: (배지) → 큰 제목 → 내용 → 아래 파란 버튼 (UI 시안 05~15) */
export const StepFrame = ({
  badge,
  heading,
  children,
  buttonLabel,
  buttonDisabled = false,
  onButton,
  confidence,
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
      {confidence ? (
        <ConfidenceButtons {...confidence} />
      ) : (
        <button
          type="button"
          // 클릭 이벤트를 넘기지 않는다 (onNext(result?)에 이벤트가 결과로 들어가 점수가 틀어졌던 버그)
          onClick={() => onButton()}
          disabled={buttonDisabled}
          className="bg-primary mt-6 w-full rounded-2xl py-4 text-base font-bold text-white transition active:scale-[0.99] disabled:bg-slate-300"
        >
          {buttonLabel}
        </button>
      )}
    </div>
  )
}

const CONFIDENCE_BASE =
  'rounded-2xl border py-4 text-base font-bold transition active:scale-[0.99] disabled:border-slate-300 disabled:bg-slate-300 disabled:text-white'

/** 정답을 보기 전에 얼마나 확신하는지 고르는 두 버튼. 누르면 바로 채점한다 */
const ConfidenceButtons = ({ disabled, onPick }: ConfidenceProps) => (
  <div className="mt-6">
    <p className="mb-2 text-center text-sm text-slate-500">
      이 답, 확실한가요? 누르면 정답을 확인해요
    </p>
    <div
      className="grid grid-cols-2 gap-2.5"
      role="group"
      aria-label="확신 정도를 고르고 정답 확인"
    >
      <button
        type="button"
        disabled={disabled}
        onClick={() => onPick(1)}
        className={`border-primary text-primary bg-white ${CONFIDENCE_BASE}`}
      >
        헷갈려요
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onPick(2)}
        className={`border-primary bg-primary text-white ${CONFIDENCE_BASE}`}
      >
        확실해요
      </button>
    </div>
  </div>
)
