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
    <section className="rounded-[28px] bg-white px-5 py-5 shadow-[0_6px_0_#dfe4f6]">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-bold text-[#232c5c]">확신 점검</h2>
        <p className="text-sm font-semibold text-[#5b6694]">답 {all.total}개</p>
      </div>
      <p className="mt-1 text-xs break-keep text-[#5b6694]">
        안다고 생각한 것과 실제로 맞힌 것이 얼마나 같은지 봐요
      </p>

      {all.total === 0 ? (
        <p className="mt-4 rounded-2xl bg-[#f0f3fc] px-4 py-6 text-center text-sm break-keep text-[#5b6694]">
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
          <p className="text-sm font-bold text-[#232c5c]">확실하다고 했는데 틀린 개념</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {sureWrongConcepts.map((name) => (
              <li
                key={name}
                className="rounded-full bg-rose-50 px-3 py-1.5 text-sm font-semibold text-rose-700"
              >
                {name}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-[#5b6694]">다시 맞히면 여기서 빠져요</p>
        </div>
      )}
    </section>
  )
}

/** 큰 글씨 한 줄: 확실해요라고 한 답의 정답률. 답이 부족하면 안내만 */
const Headline = ({ summary }: { summary: CalibrationSummary }) => {
  if (!summary.enough) {
    return (
      <p className="mt-4 rounded-2xl bg-[#f0f3fc] px-4 py-4 text-sm break-keep text-[#3a4473]">
        답이 더 쌓이면 비율을 보여 드려요. 지금은 개수만 볼 수 있어요
      </p>
    )
  }
  return (
    <div className="mt-4 rounded-2xl bg-[#f0f3fc] px-4 py-4">
      {summary.sureAccuracy !== null && (
        <p className="text-base font-bold break-keep text-[#232c5c]">
          확실해요라고 한 답 중{' '}
          <span className="text-[#3a4a99]">{percent(summary.sureAccuracy)}</span>를 맞혔어요
        </p>
      )}
      {summary.unsureAccuracy !== null && (
        <p className="mt-1 text-sm break-keep text-[#3a4473]">
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
      <tr className="text-xs font-semibold text-[#5b6694]">
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
        <th scope="row" className="text-xs font-semibold text-[#5b6694]">
          맞힘
        </th>
        <Cell count={summary.sureRight} note="알고 맞힘" />
        <Cell count={summary.unsureRight} note="알면서 망설임" />
      </tr>
      <tr>
        <th scope="row" className="text-xs font-semibold text-[#5b6694]">
          틀림
        </th>
        <Cell count={summary.sureWrong} note="안다고 착각" danger />
        <Cell count={summary.unsureWrong} note="모르는 걸 앎" />
      </tr>
    </tbody>
  </table>
)

const Cell = ({ count, note, danger }: { count: number; note: string; danger?: boolean }) => (
  <td className={`rounded-2xl px-2 py-3 ${danger ? 'bg-rose-50' : 'bg-[#f0f3fc]'}`}>
    <p className={`text-xl font-bold ${danger ? 'text-rose-700' : 'text-[#232c5c]'}`}>{count}</p>
    <p className={`mt-0.5 text-xs ${danger ? 'font-semibold text-rose-700' : 'text-[#5b6694]'}`}>
      {note}
    </p>
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
    <p className="mt-4 text-sm break-keep text-[#3a4473]">
      최근 {days}일 동안 틀린 답 중 확실해요였던 비율이{' '}
      <span className="font-bold text-[#232c5c]">
        {before}% → {now}%
      </span>
      로 {word}
    </p>
  )
}
