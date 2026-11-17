import type { JudgementFeedback, JudgementGrade } from '@/types/card'

/** 루브릭 기준. desc 는 Claude 채점 이유가 없을 때 보여 줄 기준 설명 */
const RUBRIC = [
  { key: 'evidence', label: '증거', max: 2, desc: '뉴스 속 구체적인 사실을 근거로 썼는지 봐요.' },
  { key: 'reasoning', label: '추론', max: 4, desc: '개념을 사슬로 이어 판단까지 연결했는지 봐요.' },
  { key: 'rebuttal', label: '반박', max: 3, desc: '다른 힘(위험)까지 고려했는지 봐요.' },
] as const

/**
 * AI 분석: 판단해보기 제출 후 결과 화면에 나온다 (A의 /api/judgement 응답, UI 시안 16 모양).
 * - 채점됨: 잘한 점 → 더 생각할 점 → 인과 뼈대 → 판단 근거 채점(기준별 점수·이유)
 * - 채점 서버 실패·하루 한도 초과: 점수 없이 message 만
 * - 피드백이 없으면(null) 채점까지만
 */
export const AiAnalysis = ({ grade }: { grade: JudgementGrade }) => {
  const { score, rubric, reasons, feedback } = grade

  return (
    <section className="rounded-3xl bg-slate-100 px-5 py-5">
      <h3 className="text-lg font-bold text-slate-900">AI 피드백</h3>

      {score === null ? (
        <p className="mt-2 text-sm leading-relaxed text-slate-600">{grade.message}</p>
      ) : (
        <>
          {feedback && <FeedbackBody feedback={feedback} />}

          {rubric && (
            <div className={feedback ? 'mt-4 border-t border-slate-200 pt-4' : 'mt-3'}>
              <div className="flex items-baseline justify-between">
                <p className="text-primary font-bold">판단 근거 채점</p>
                <p className="text-primary font-bold tabular-nums">적용판단 {score}점</p>
              </div>
              <dl className="mt-3 flex flex-col gap-2.5">
                {RUBRIC.map(({ key, label, max, desc }) => (
                  <div key={key} className="flex items-start gap-3">
                    <dt className="text-primary shrink-0 rounded-lg bg-blue-100 px-2.5 py-1 text-sm font-bold tabular-nums">
                      {label} {rubric[key]}/{max}
                    </dt>
                    <dd className="pt-0.5 text-sm leading-relaxed text-slate-700">
                      {(key !== 'evidence' && reasons[key]) || desc}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
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
      <p className="mt-2 leading-relaxed text-slate-700">{feedback.good}</p>

      <div className="mt-4 border-t border-slate-200 pt-4">
        <p className="font-bold text-amber-700">더 생각할 점</p>
        <p className="mt-1.5 leading-relaxed text-slate-700">{feedback.thinkMore}</p>
      </div>

      {feedback.chain.length > 0 && (
        <div className="mt-4 border-t border-slate-200 pt-4">
          <p className="font-bold text-slate-900">인과 뼈대</p>
          {/* 카드의 인과 경로 순서. 근거에 쓰지 않은 개념은 점선으로 흐리게 */}
          <ol className="mt-2 flex flex-wrap items-center gap-1 text-sm">
            {feedback.chain.map((c, i) => (
              <li key={c.name} className="flex items-center gap-1">
                {i > 0 && <span className="text-slate-400">→</span>}
                <span
                  className={
                    c.used
                      ? 'rounded-full bg-white px-3 py-1 font-semibold text-slate-800'
                      : 'rounded-full border border-dashed border-slate-300 px-3 py-1 text-slate-400'
                  }
                >
                  {c.name}
                </span>
              </li>
            ))}
          </ol>
          {feedback.chain.some((c) => !c.used) && (
            <p className="mt-1.5 text-xs text-slate-400">점선은 근거에서 빠진 개념이에요.</p>
          )}
          {feedback.chainComment && (
            <p className="mt-2 text-sm leading-relaxed text-slate-700">{feedback.chainComment}</p>
          )}
        </div>
      )}
    </>
  )
}
