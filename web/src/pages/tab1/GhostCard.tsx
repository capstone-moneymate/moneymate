import { reviewLabel } from '@/lib/review'
import type { CardDetail } from '@/types/card'
import type { GhostCell, GhostComparison, GhostRow } from '@/types/ghost'

/**
 * 결과 화면의 고스트 비교 (추가 구현 2-6): 같은 카드를 다시 풀었을 때 지난번과 이번을 단계별로 나란히 보여 준다.
 * 숫자와 "좋아졌다"·"최고 기록" 판단은 서버 값이고(server answer/Ghost), 화면은 문장으로 옮기기만 한다.
 * 말투는 사실만 쓴다 ("맞힘 · 12초"). 같은 문제라 기억해서 빨라졌을 수 있다는 점을 아래에 적는다.
 */
export const GhostCard = ({
  card,
  comparison,
}: {
  card: CardDetail
  comparison: GhostComparison
}) => {
  const { previous, current, rows, improvedSteps } = comparison
  const last = `지난번(${reviewLabel(previous.date)})`
  const fewerSureWrong =
    previous.sureWrong !== null &&
    current.sureWrong !== null &&
    current.sureWrong < previous.sureWrong
  // 정답·시간이 먼저, 그다음이 확신 (계획 2-6 의 판단 순서)
  const headline =
    improvedSteps > 0
      ? `${last}보다 ${improvedSteps}단계 좋아졌어요`
      : fewerSureWrong
        ? `${last}보다 확실하다고 하고 틀린 답이 줄었어요`
        : `${last} 기록과 나란히 봤어요`
  const labels = stepLabels(card)
  const best = rows.filter((r) => r.best)

  return (
    <section>
      <div className="mm-h-sec">
        <h3>지난번의 나와 비교</h3>
      </div>
      <div className="mm-box px-4 py-3.5">
        <p className="text-base font-extrabold break-keep">{headline}</p>
        {best.length > 0 && (
          <p className="text-blue-ink mt-1 text-sm font-extrabold break-keep">
            {best.map((r) => labels[r.stepId] ?? KIND_LABEL[r.kind]).join(', ')} 최고 기록 경신
          </p>
        )}

        <table className="mt-3 w-full table-fixed text-sm">
          <caption className="sr-only">단계별 지난번 기록과 이번 기록</caption>
          <thead>
            <tr className="text-sub text-xs">
              <td className="w-[30%]" />
              <th scope="col" className="py-1 text-left font-semibold">
                지난번
              </th>
              <th scope="col" className="py-1 text-left font-semibold">
                이번
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.stepId} className="border-line border-t-2">
                <th scope="row" className="py-2.5 text-left font-bold">
                  {labels[row.stepId] ?? KIND_LABEL[row.kind]}
                </th>
                <td className="text-sub py-2.5 font-medium tabular-nums">
                  {cellText(row, row.previous)}
                </td>
                <td
                  className={`py-2.5 tabular-nums ${row.improved ? 'text-blue-ink font-extrabold' : 'font-medium'}`}
                >
                  {cellText(row, row.current)}
                  {row.best && <span className="sr-only"> (최고 기록)</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {previous.sureWrong !== null && current.sureWrong !== null && (
          <p className="border-line mt-1 border-t-2 pt-3 text-sm font-semibold break-keep">
            확실해요인데 틀림: 지난번 {previous.sureWrong}개 → 이번 {current.sureWrong}개
          </p>
        )}
        <p className="text-faint mt-3 text-xs font-semibold break-keep">
          같은 문제를 다시 푼 기록이에요. 문제를 기억해서 빨라졌을 수도 있어요.
        </p>
      </div>
    </section>
  )
}

const KIND_LABEL: Record<GhostRow['kind'], string> = {
  quiz: '퀴즈',
  chart: '차트 읽기',
  causal_order: '인과 순서',
  judgement: '판단해보기',
}

/** 단계 id → 줄 이름. 퀴즈가 여러 개면 "퀴즈 1", "퀴즈 2" */
const stepLabels = (card: CardDetail): Record<string, string> => {
  const quizzes = card.steps.filter((s) => s.kind === 'quiz')
  const labels: Record<string, string> = {}
  for (const s of card.steps) {
    if (s.kind === 'concept') continue
    labels[s.id] =
      s.kind === 'quiz' && quizzes.length > 1
        ? `퀴즈 ${quizzes.indexOf(s) + 1}`
        : KIND_LABEL[s.kind]
  }
  return labels
}

/** "맞힘 · 12초", "틀림", "71점". 기록이 없으면 "-" */
const cellText = (row: GhostRow, cell: GhostCell | null): string => {
  if (!cell) return '-'
  if (row.kind === 'judgement') return cell.score === null ? '-' : `${cell.score}점`
  if (cell.isCorrect === null) return '-'
  const mark = cell.isCorrect ? '맞힘' : '틀림'
  return cell.seconds === null ? mark : `${mark} · ${cell.seconds}초`
}
