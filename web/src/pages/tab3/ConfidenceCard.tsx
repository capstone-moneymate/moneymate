import type { Calibration, CalibrationSummary } from '@/types/learner'

const percent = (x: number) => `${Math.round(x * 100)}%`

/**
 * 마이페이지 "확신 점검" (추가 구현 2-5·2-7). [헷갈려요] [확실해요]로 낸 답을 정답/오답과 맞춰 본 2 × 2 표다.
 * 개수와 비율은 모두 서버 값이고(learner/calibration.py), 화면은 % 로 바꿔 표기만 한다.
 * 답이 충분하지 않으면(enough = false) 비율은 보여 주지 않고 개수만 보여 준다.
 */
export const ConfidenceCard = ({ calibration }: { calibration: Calibration }) => {
  const { all, recent, earlier, recentDays, sureWrongConcepts } = calibration

  return (
    <section className="mm-box rounded-[22px] px-5 py-5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-ink text-lg font-bold">확신 점검</h2>
        <p className="text-sub text-sm font-semibold">답 {all.total}개</p>
      </div>
      <p className="text-sub mt-1 text-xs break-keep">
        안다고 생각한 것과 실제로 맞힌 것이 얼마나 같은지 봐요
      </p>

      {all.total === 0 ? (
        <p className="bg-mist text-sub mt-4 rounded-2xl px-4 py-6 text-center text-sm break-keep">
          문제를 풀 때 [헷갈려요] [확실해요]를 누르면 여기에 쌓여요
        </p>
      ) : (
        <>
          <Headline summary={all} />
          <Table summary={all} />
          <Trend recent={recent} earlier={earlier} days={recentDays} />
        </>
      )}

      {sureWrongConcepts.length > 0 && (
        <div className="mt-5">
          <p className="text-ink text-sm font-bold">확실하다고 했는데 틀린 개념</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {sureWrongConcepts.map((name) => (
              <li
                key={name}
                className="bg-no-soft text-no-ink rounded-full px-3 py-1.5 text-sm font-semibold"
              >
                {name}
              </li>
            ))}
          </ul>
          <p className="text-sub mt-2 text-xs">다시 맞히면 여기서 빠져요</p>
        </div>
      )}
    </section>
  )
}

/** 큰 글씨 한 줄: 확실해요라고 한 답의 정답률. 답이 부족하면 안내만 */
const Headline = ({ summary }: { summary: CalibrationSummary }) => {
  if (!summary.enough) {
    return (
      <p className="bg-mist text-ink mt-4 rounded-2xl px-4 py-4 text-sm break-keep">
        답이 더 쌓이면 비율을 보여 드려요. 지금은 개수만 볼 수 있어요
      </p>
    )
  }
  return (
    <div className="bg-mist mt-4 rounded-2xl px-4 py-4">
      {summary.sureAccuracy !== null && (
        <p className="text-ink text-base font-bold break-keep">
          확실해요라고 한 답 중{' '}
          <span className="text-blue-ink">{percent(summary.sureAccuracy)}</span>를 맞혔어요
        </p>
      )}
      {summary.unsureAccuracy !== null && (
        <p className="text-ink mt-1 text-sm break-keep">
          헷갈려요라고 한 답은 {percent(summary.unsureAccuracy)}를 맞혔어요
        </p>
      )}
    </div>
  )
}

/** 정답/오답 × 확실/헷갈려요 개수. "확실해요인데 틀림" 칸만 붉게 */
const Table = ({ summary }: { summary: CalibrationSummary }) => (
  <table className="mt-4 w-full table-fixed border-separate border-spacing-1.5 text-center text-sm">
    <caption className="sr-only">확신과 정답 여부로 나눈 답 개수</caption>
    <thead>
      <tr className="text-sub text-xs font-semibold">
        <td />
        <th scope="col" className="font-semibold">
          확실해요
        </th>
        <th scope="col" className="font-semibold">
          헷갈려요
        </th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <th scope="row" className="text-sub text-xs font-semibold">
          맞힘
        </th>
        <Cell count={summary.sureRight} note="알고 맞힘" />
        <Cell count={summary.unsureRight} note="알면서 망설임" />
      </tr>
      <tr>
        <th scope="row" className="text-sub text-xs font-semibold">
          틀림
        </th>
        <Cell count={summary.sureWrong} note="안다고 착각" danger />
        <Cell count={summary.unsureWrong} note="모르는 걸 앎" />
      </tr>
    </tbody>
  </table>
)

const Cell = ({ count, note, danger }: { count: number; note: string; danger?: boolean }) => (
  <td className={`rounded-2xl px-2 py-3 ${danger ? 'bg-no-soft' : 'bg-mist'}`}>
    <p className={`text-xl font-bold ${danger ? 'text-no-ink' : 'text-ink'}`}>{count}</p>
    <p className={`mt-0.5 text-xs ${danger ? 'text-no-ink font-semibold' : 'text-sub'}`}>{note}</p>
  </td>
)

/** 틀린 답 중 확실해요 비율이 이전보다 줄었는지. 두 기간 모두 답이 충분할 때만 보여 준다 */
const Trend = ({
  recent,
  earlier,
  days,
}: {
  recent: CalibrationSummary
  earlier: CalibrationSummary
  days: number
}) => {
  if (!recent.enough || !earlier.enough || recent.illusion === null || earlier.illusion === null) {
    return null
  }
  const before = Math.round(earlier.illusion * 100)
  const now = Math.round(recent.illusion * 100)
  const word = now < before ? '줄었어요' : now > before ? '늘었어요' : '그대로예요'
  return (
    <p className="text-ink mt-4 text-sm break-keep">
      최근 {days}일 동안 틀린 답 중 확실해요였던 비율이{' '}
      <span className="text-ink font-bold">
        {before}% → {now}%
      </span>
      로 {word}
    </p>
  )
}
