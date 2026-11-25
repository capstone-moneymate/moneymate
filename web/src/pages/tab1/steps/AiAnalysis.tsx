import type { JudgementFeedback, JudgementGrade } from '@/types/card'

/** 루브릭 기준. desc 는 Claude 채점 이유가 없을 때 보여 줄 기준 설명 */
const RUBRIC = [
  { key: 'evidence', label: '증거', max: 2, desc: '뉴스 속 구체적인 사실을 근거로 썼는지 봐요.' },
  { key: 'reasoning', label: '추론', max: 4, desc: '개념을 사슬로 이어 판단까지 연결했는지 봐요.' },
  { key: 'rebuttal', label: '반박', max: 3, desc: '다른 힘(위험)까지 고려했는지 봐요.' },
] as const

/**
 * AI 분석: 판단해보기 제출 후 결과 화면에 나온다 (A의 /api/judgement 응답, UI 시안 app.html 의 피드백 칸 모양).
 * - 채점됨: 잘한 점 → 더 생각할 점(노란 칸) → 인과 뼈대 → 근거 점수(기준별 점수·이유)
 * - 채점 서버 실패·하루 한도 초과: 점수 없이 message 만
 * - 피드백이 없으면(null) 채점까지만
 */
export const AiAnalysis = ({ grade }: { grade: JudgementGrade }) => {
  const { score, rubric, reasons, feedback } = grade

  return (
    <section>
      <div className="mm-h-sec">
        <h3>AI 피드백</h3>
      </div>

      {score === null ? (
        <div className="mm-box mm-fb mt-0">
          <p>{grade.message}</p>
        </div>
      ) : (
        <>
          {feedback && <FeedbackBody feedback={feedback} />}

          {rubric && (
            <div className={`mm-box mm-fb ${feedback ? '' : 'mt-0'}`}>
              <h4>
                근거 점수<em>{score}점</em>
              </h4>
              <dl className="mm-rub">
                {RUBRIC.map(({ key, label, max, desc }) => (
                  <div key={key} className={rubric[key] < max ? 'low' : ''}>
                    <dt>
                      {label} {rubric[key]}/{max}
                    </dt>
                    <dd>{(key !== 'evidence' && reasons[key]) || desc}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
          {grade.grader === 'rule' && (
            <p className="text-faint mt-2.5 text-xs font-semibold">
              지금은 AI 채점을 쓸 수 없어 키워드 규칙으로 채점했어요.
            </p>
          )}
        </>
      )}
      <p className="text-faint mt-2.5 text-xs font-semibold">
        선택 자체는 채점하지 않고, 근거의 질만 봐요.
      </p>
    </section>
  )
}

const FeedbackBody = ({ feedback }: { feedback: JudgementFeedback }) => {
  return (
    <>
      <div className="mm-box mm-fb mt-0">
        <h4>잘한 점</h4>
        <p>{feedback.good}</p>
      </div>

      <div className="mm-box mm-fb also">
        <h4>더 생각할 점</h4>
        <p>{feedback.thinkMore}</p>
      </div>

      {feedback.chain.length > 0 && (
        <div className="mm-box mm-fb">
          <h4>인과 뼈대</h4>
          {/* 카드의 인과 경로 순서. 근거에 쓰지 않은 개념은 점선으로 흐리게 */}
          <ol className="mt-2 flex flex-wrap items-center gap-1 text-sm">
            {feedback.chain.map((c, i) => (
              <li key={c.name} className="flex items-center gap-1">
                {i > 0 && <span className="text-faint">→</span>}
                <span
                  className={
                    c.used
                      ? 'bg-blue-soft text-blue-ink rounded-full px-3 py-1 font-extrabold'
                      : 'text-faint rounded-full border-2 border-dashed border-[#c6ceda] px-3 py-0.5 font-semibold'
                  }
                >
                  {c.name}
                </span>
              </li>
            ))}
          </ol>
          {feedback.chain.some((c) => !c.used) && (
            <p className="text-faint mt-1.5 text-xs font-semibold">
              점선은 근거에서 빠진 개념이에요.
            </p>
          )}
          {feedback.chainComment && <p className="mt-2">{feedback.chainComment}</p>}
        </div>
      )}
    </>
  )
}
