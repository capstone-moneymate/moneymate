import type { JudgementFeedback, JudgementGrade } from '@/types/card'

const RUBRIC = [
  { key: 'evidence', label: '증거', max: 2 },
  { key: 'reasoning', label: '추론', max: 4 },
  { key: 'rebuttal', label: '반박', max: 3 },
] as const

/**
 * AI 분석: 판단해보기 제출 후 결과 화면에 나온다 (A의 /api/judgement 응답).
 * - 채점됨: 점수 + 기준별 점수·이유 + 잘한 점 · 더 생각할 점 · 인과 뼈대
 * - 채점 서버 실패·하루 한도 초과: 점수 없이 message 만
 * - 피드백이 없으면(null) 점수까지만
 */
export const AiAnalysis = ({ grade }: { grade: JudgementGrade }) => {
  const { score, rubric, reasons, feedback } = grade

  return (
    <section className="rounded-2xl bg-slate-50 px-4 py-4">
      <div className="flex items-baseline justify-between">
        <h3 className="font-bold text-slate-900">AI 분석</h3>
        {score !== null && (
          <span className="text-primary text-lg font-bold tabular-nums">{score}점</span>
        )}
      </div>

      {score === null ? (
        <p className="mt-2 text-sm text-slate-600">{grade.message}</p>
      ) : (
        <>
          {rubric && (
            <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
              {RUBRIC.map(({ key, label, max }) => (
                <div key={key} className="rounded-xl bg-white py-2">
                  <dt className="text-xs text-slate-500">{label}</dt>
                  <dd className="text-sm font-bold text-slate-900 tabular-nums">
                    {rubric[key]} / {max}
                  </dd>
                </div>
              ))}
            </dl>
          )}
          {(reasons.reasoning || reasons.rebuttal) && (
            <ul className="mt-2 flex flex-col gap-1 text-xs text-slate-500">
              {reasons.reasoning && <li>추론 · {reasons.reasoning}</li>}
              {reasons.rebuttal && <li>반박 · {reasons.rebuttal}</li>}
            </ul>
          )}
          {feedback && <FeedbackBody feedback={feedback} />}
          {grade.grader === 'rule' && (
            <p className="mt-3 text-xs text-slate-400">
              지금은 AI 채점을 쓸 수 없어 키워드 규칙으로 채점했어요.
            </p>
          )}
        </>
      )}
      <p className="mt-4 text-xs text-slate-400">선택 자체는 채점하지 않고, 근거의 질만 봐요.</p>
    </section>
  )
}

const FeedbackBody = ({ feedback }: { feedback: JudgementFeedback }) => {
  return (
    <>
      <p className="mt-4 text-sm font-semibold text-slate-800">잘한 점</p>
      <p className="mt-0.5 text-sm text-slate-600">{feedback.good}</p>
      <p className="mt-3 text-sm font-semibold text-slate-800">더 생각할 점</p>
      <p className="mt-0.5 text-sm text-slate-600">{feedback.thinkMore}</p>
      {feedback.chain.length > 0 && (
        <>
          <p className="mt-3 text-sm font-semibold text-slate-800">인과 뼈대</p>
          {/* 카드의 인과 경로 순서. 근거에 쓰지 않은 개념은 점선으로 흐리게 */}
          <ol className="mt-1.5 flex flex-wrap items-center gap-1 text-xs">
            {feedback.chain.map((c, i) => (
              <li key={c.name} className="flex items-center gap-1">
                {i > 0 && <span className="text-slate-400">→</span>}
                <span
                  className={
                    c.used
                      ? 'rounded-full bg-white px-2.5 py-1 font-semibold text-slate-800'
                      : 'rounded-full border border-dashed border-slate-300 px-2.5 py-1 text-slate-400'
                  }
                >
                  {c.name}
                </span>
              </li>
            ))}
          </ol>
          {feedback.chain.some((c) => !c.used) && (
            <p className="mt-1 text-xs text-slate-400">점선은 근거에서 빠진 개념이에요.</p>
          )}
          {feedback.chainComment && (
            <p className="mt-1.5 text-sm text-slate-600">{feedback.chainComment}</p>
          )}
        </>
      )}
    </>
  )
}
