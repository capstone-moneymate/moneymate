import { useState } from 'react'
import { useSubmitAnswer } from '@/api/cards'
import { DailyLimitError } from '@/api/client'
import type { AnswerResult, JudgementStep, PastAnswer, PastInput } from '@/types/card'
import { NotAnswered } from '@/pages/tab1/steps/AnswerFeedback'
import { StepFrame } from '@/pages/tab1/steps/StepFrame'

/** 근거 최소 글자 수. 근거 작성은 필수 (기술확정안 루브릭) */
const MIN_REASON = 5

interface ReasonViewProps {
  step: JudgementStep
  onNext: (result?: AnswerResult, input?: PastInput) => void
  /**
   * 풀었던 내용 보기(탭3). 있으면 그때 고른 판단·근거를 읽기 전용으로 보여 주고 다시 채점하지 않는다
   * (채점 결과·AI 피드백은 결과 화면). null = 그날 안 풀었음, undefined = 평소처럼 푼다
   */
  past?: PastAnswer | null
}

/** 판단해보기(선택 + 근거). 선택은 채점하지 않고 근거만 루브릭으로 채점한다 */
export const ReasonView = ({ step, onNext, past }: ReasonViewProps) => {
  const reviewing = past !== undefined
  const pastInput = past?.input.kind === 'judgement' ? past.input : null
  // 서버에는 고른 문장만 저장돼 있어 보기 목록에서 같은 문장을 찾는다
  const pastChoice = pastInput?.choice ? step.choices.indexOf(pastInput.choice) : -1
  const [choice, setChoice] = useState<number | null>(pastChoice >= 0 ? pastChoice : null)
  const [reason, setReason] = useState(pastInput?.reason ?? '')
  const score = past?.result.grade?.score
  const submit = useSubmitAnswer()
  const ready = choice !== null && reason.trim().length >= MIN_REASON

  const limited = submit.error instanceof DailyLimitError ? submit.error.message : null

  const send = () => {
    if (choice === null) return
    const answer = {
      kind: 'judgement' as const,
      choiceIndex: choice,
      choice: step.choices[choice],
      reason: reason.trim(),
    }
    submit.mutate(
      { stepId: step.id, answer },
      {
        onSuccess: (result) =>
          onNext(result, { kind: 'judgement', choice: answer.choice, reason: answer.reason }),
      },
    )
  }

  // 하루 채점 횟수를 다 쓰면 채점 없이 결과 화면으로 넘어간다 (결과 화면은 message 만 보여 준다)
  const skipGrading = (message: string) =>
    onNext({
      stepId: step.id,
      isCorrect: null,
      grade: {
        score: null,
        correct: null,
        rubric: null,
        reasons: {},
        grader: null,
        reused: false,
        message,
        feedback: null,
      },
    })

  return (
    <StepFrame
      badge="마지막 · 내 판단 적어보기"
      heading={step.question}
      mood="smile"
      buttonLabel={
        reviewing
          ? past
            ? '피드백 다시 보기'
            : '다음'
          : submit.isPending
            ? '채점 중…'
            : '제출하고 피드백 받기'
      }
      buttonDisabled={!reviewing && (!ready || submit.isPending)}
      onButton={() => (reviewing ? onNext(past?.result) : send())}
    >
      {/* UI 시안 app.html 의 판단 화면: 상황 설명(회색 칸) → 나의 판단 → 근거 */}
      {step.context && <p className="mm-ctx mt-0">{step.context}</p>}

      {step.choices.length > 0 && (
        <ul className="mm-opts mt-3" aria-label="나의 판단">
          {step.choices.map((c, i) => (
            <li key={c}>
              <button
                type="button"
                disabled={reviewing}
                onClick={() => setChoice(i)}
                aria-pressed={choice === i}
                className="mm-opt min-h-[52px]"
              >
                {c}
              </button>
            </li>
          ))}
        </ul>
      )}

      <label className="mm-reason">
        <span>
          <b>
            왜 그렇게 생각했나요? <i>(필수)</i>
          </b>
          {!reviewing && (
            <em>
              {reason.trim().length}자 / 최소 {MIN_REASON}자
            </em>
          )}
        </span>
        <textarea
          value={reason}
          readOnly={reviewing}
          onChange={(e) => setReason(e.target.value)}
          placeholder="뉴스 속 사실과 오늘 배운 개념을 넣어서 이유를 써 보세요"
        />
      </label>
      {past === null && <NotAnswered />}
      {reviewing && past && (
        <p className="text-sub mt-2 text-sm font-bold">
          {score == null ? '이 답안은 채점하지 못했어요' : `그때 적용판단 점수 ${score}점`}
        </p>
      )}
      {!reviewing && (
        <p className="text-faint mt-2 text-xs font-semibold">근거로 적용판단 점수를 매겨요</p>
      )}
      {limited ? (
        <div className="mm-ctx text-sm">
          <p>{limited}</p>
          <button
            type="button"
            onClick={() => skipGrading(limited)}
            className="text-blue-ink mt-1.5 font-extrabold underline underline-offset-4"
          >
            채점 없이 결과 보기
          </button>
        </div>
      ) : (
        submit.isError && (
          <p className="text-no-ink mt-2 text-sm font-bold">채점하지 못했어요. 다시 눌러 주세요.</p>
        )
      )}
    </StepFrame>
  )
}
