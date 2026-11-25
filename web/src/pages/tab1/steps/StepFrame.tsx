import type { ReactNode } from 'react'
import { Mate, type MateMood } from '@/components/Mate'
import type { AnswerResult, Confidence } from '@/types/card'
import { AnswerFeedback } from '@/pages/tab1/steps/AnswerFeedback'

interface StepFrameProps {
  /** 말풍선 위 작은 글자 (예: "퀴즈 1 / 2", "순서 맞추기") */
  badge?: string
  /** 말풍선 안 큰 글자 (질문·제목) */
  heading?: string
  /** 마스코트 표정. 채점 결과가 있으면 맞음 → 웃음, 틀림 → 생각 중으로 바뀐다 */
  mood?: MateMood
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
  /** 채점 결과. 있으면 아래 칸이 초록(맞음)·빨강(틀림)으로 바뀌고 해설을 버튼 위에 보여 준다 */
  feedback?: { result: AnswerResult; correctText?: string }
}

interface ConfidenceProps {
  disabled: boolean
  onPick: (confidence: Confidence) => void
}

/**
 * 단계 화면 공통 틀 (UI 시안 app.html 의 학습 화면):
 * 마스코트 말풍선(작은 글자 + 질문) → 내용(스크롤) → 아래에 붙어 있는 버튼 칸.
 * 채점 뒤에는 아래 칸이 색 칸으로 올라와 맞음·틀림과 해설을 보여 준다
 */
export const StepFrame = ({
  badge,
  heading,
  mood,
  children,
  buttonLabel,
  buttonDisabled = false,
  onButton,
  confidence,
  feedback,
}: StepFrameProps) => {
  const ok = feedback ? feedback.result.isCorrect === true : null
  const face: MateMood = ok === null ? (mood ?? 'think') : ok ? 'happy' : 'think'

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mm-l-body">
          {(badge || heading) && (
            <div className="mm-say">
              <Mate mood={face} />
              <div className="mm-bub">
                {badge && <small>{badge}</small>}
                {heading && <p>{heading}</p>}
              </div>
            </div>
          )}
          <div className="mt-3.5">{children}</div>
        </div>
      </div>

      {confidence ? (
        <ConfidenceButtons {...confidence} />
      ) : (
        <div
          className={`mm-l-foot ${ok === null ? '' : `${ok ? 'ok' : 'no'} max-h-[62%] overflow-y-auto`}`}
        >
          {feedback && <AnswerFeedback {...feedback} />}
          <button
            type="button"
            // 클릭 이벤트를 넘기지 않는다 (onNext(result?)에 이벤트가 결과로 들어가 점수가 틀어졌던 버그)
            onClick={() => onButton()}
            disabled={buttonDisabled}
            className="mm-btn"
          >
            {buttonLabel}
          </button>
        </div>
      )}
    </div>
  )
}

/** 정답을 보기 전에 얼마나 확신하는지 고르는 두 버튼. 누르면 바로 채점한다 */
const ConfidenceButtons = ({ disabled, onPick }: ConfidenceProps) => (
  <div className="mm-l-foot">
    <p className="text-sub text-center text-[13px] font-semibold">
      이 답, 확실한가요? 누르면 정답을 확인해요
    </p>
    <div className="mm-two" role="group" aria-label="확신 정도를 고르고 정답 확인">
      <button type="button" disabled={disabled} onClick={() => onPick(1)} className="mm-btn ghost">
        헷갈려요
      </button>
      <button type="button" disabled={disabled} onClick={() => onPick(2)} className="mm-btn">
        확실해요
      </button>
    </div>
  </div>
)
