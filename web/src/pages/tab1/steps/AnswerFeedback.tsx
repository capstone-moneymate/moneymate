import type { AnswerResult } from '@/types/card'

interface AnswerFeedbackProps {
  result: AnswerResult
  /** 틀렸을 때 보여 줄 정답 문장 */
  correctText?: string
}

/**
 * 코드 채점 단계(퀴즈·인과 순서·차트)의 맞음·틀림 + 해설.
 * 학습 화면 아래에서 올라오는 색 칸(StepFrame 의 feedback) 안에 들어간다 (UI 시안 app.html 의 .verdict·.why)
 */
export const AnswerFeedback = ({ result, correctText }: AnswerFeedbackProps) => {
  const ok = result.isCorrect === true
  return (
    <div role="status">
      <p className="mm-verdict">
        <VerdictIcon ok={ok} />
        {ok ? '정답이에요!' : '아쉬워요'}
      </p>
      <p className="mm-why">
        {!ok && correctText && (
          <>
            <b>정답: {correctText}</b>
            <br />
          </>
        )}
        {result.explanation}
      </p>
    </div>
  )
}

/** 동그라미 안의 ✓(맞음) / ×(틀림). 색은 글자색을 따른다 */
export const VerdictIcon = ({ ok }: { ok: boolean }) => (
  <svg viewBox="0 0 30 30" aria-hidden>
    <circle cx="15" cy="15" r="15" fill="currentColor" />
    <path
      d={ok ? 'M9 15.5l4 4 8-9' : 'M10 10l10 10M20 10L10 20'}
      fill="none"
      stroke="#fff"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

/** 풀었던 내용 보기에서 그날 이 문제를 안 풀었을 때 */
export const NotAnswered = () => (
  <p role="status" className="mm-ctx text-sub text-sm">
    이 날은 이 문제를 풀지 않았어요.
  </p>
)
