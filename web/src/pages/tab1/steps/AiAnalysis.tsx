import type { RubricGrade } from '@/types/card'

const RUBRIC = [
  { key: 'evidence', label: '증거', max: 2 },
  { key: 'reasoning', label: '추론', max: 3 },
  { key: 'rebuttal', label: '반박', max: 2 },
] as const

/** AI 분석: 루브릭 점수 + 잘한 점 · 더 생각할 점 · 인과 뼈대. 유형 3 단계 화면과 결과 화면이 같이 쓴다 */
export const AiAnalysis = ({ grade }: { grade: RubricGrade }) => {
  return (
    <section className="rounded-2xl bg-slate-50 px-4 py-4">
      <div className="flex items-baseline justify-between">
        <h3 className="font-bold text-slate-900">AI 분석</h3>
        <span className="text-primary text-lg font-bold tabular-nums">{grade.score}점</span>
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
        {RUBRIC.map(({ key, label, max }) => (
          <div key={key} className="rounded-xl bg-white py-2">
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="text-sm font-bold text-slate-900 tabular-nums">
              {grade.rubric[key]} / {max}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-sm font-semibold text-slate-800">잘한 점</p>
      <p className="mt-0.5 text-sm text-slate-600">{grade.feedback.good}</p>
      <p className="mt-3 text-sm font-semibold text-slate-800">더 생각할 점</p>
      <p className="mt-0.5 text-sm text-slate-600">{grade.feedback.consider}</p>
      {grade.feedback.skeleton.length > 0 && (
        <>
          <p className="mt-3 text-sm font-semibold text-slate-800">인과 뼈대</p>
          <p className="mt-0.5 text-sm text-slate-600">{grade.feedback.skeleton.join(' → ')}</p>
        </>
      )}
      <p className="mt-4 text-xs text-slate-400">선택 자체는 채점하지 않고, 근거의 질만 봐요.</p>
    </section>
  )
}
