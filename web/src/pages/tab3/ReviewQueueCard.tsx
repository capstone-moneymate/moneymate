import { Link } from 'react-router'
import type { ReviewItem, ReviewQueue } from '@/types/learner'

const percent = (x: number) => `${Math.round(x * 100)}%`

/**
 * 마이페이지 "오늘의 복습" (추가 구현 2-7). 서버가 정한 순서 그대로 보여 준다:
 * 확실해요라고 했는데 틀린 개념 먼저, 나머지는 지금 기억 확률이 낮은 순, 하루 상한까지.
 * 기억 확률·순서·개수는 모두 서버 값이고 화면은 % 로 바꿔 표기만 한다.
 * [복습 시작]을 누르면 이 순서대로 개념마다 새 문제를 하나씩 푼다 (ReviewPage).
 */
export const ReviewQueueCard = ({ queue }: { queue: ReviewQueue }) => {
  const waiting = queue.dueTotal - queue.items.length

  return (
    <section className="rounded-[28px] bg-white px-5 py-5 shadow-[0_6px_0_#dfe4f6]">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-bold text-[#232c5c]">오늘의 복습</h2>
        <p className="text-sm font-semibold text-[#5b6694]">
          {queue.items.length}개 · 하루 {queue.limit}개까지
        </p>
      </div>
      <p className="mt-1 text-xs break-keep text-[#5b6694]">
        잊을 때쯤 된 개념이에요. 확실하다고 했는데 틀린 개념이 맨 앞에 나와요
      </p>

      {queue.items.length === 0 ? (
        <p className="mt-4 rounded-2xl bg-[#f0f3fc] px-4 py-6 text-center text-sm break-keep text-[#5b6694]">
          {queue.dueTotal > 0
            ? '오늘 복습을 다 했어요. 남은 개념은 내일 나와요'
            : '오늘은 복습할 개념이 없어요. 문제를 풀면 잊을 때쯤 여기에 다시 나와요'}
        </p>
      ) : (
        <ol className="mt-4 space-y-2">
          {queue.items.map((item, i) => (
            <li key={item.nodeId}>
              <ReviewRow item={item} order={i + 1} />
            </li>
          ))}
        </ol>
      )}

      {queue.items.length > 0 && (
        <Link
          to="/mypage/review"
          className="mt-4 block w-full rounded-2xl bg-[#3a4a99] py-3.5 text-center font-bold text-white"
        >
          복습 시작 · 개념마다 1문제
        </Link>
      )}

      {(queue.doneToday > 0 || waiting > 0) && (
        <p className="mt-3 text-xs text-[#5b6694]">
          {queue.doneToday > 0 && `오늘 ${queue.doneToday}개 복습했어요. `}
          {waiting > 0 && `복습일이 된 개념이 ${waiting}개 더 있어요`}
        </p>
      )}
    </section>
  )
}

const ReviewRow = ({ item, order }: { item: ReviewItem; order: number }) => {
  const sureWrong = item.reason === 'sure_wrong'
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-[#f0f3fc] px-4 py-3">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-white text-sm font-bold text-[#3a4a99]">
        {order}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-bold text-[#232c5c]">{item.concept}</p>
        <p
          className={`mt-0.5 text-xs font-semibold ${sureWrong ? 'text-rose-600' : 'text-[#5b6694]'}`}
        >
          {sureWrong ? '확실하다고 했는데 틀렸어요' : '잊을 때가 됐어요'}
        </p>
      </div>
      <div className="shrink-0 text-right">
        <p className="text-xs text-[#5b6694]">기억 확률</p>
        <p className="text-base font-bold text-[#232c5c]">{percent(item.retrievability)}</p>
      </div>
    </div>
  )
}
