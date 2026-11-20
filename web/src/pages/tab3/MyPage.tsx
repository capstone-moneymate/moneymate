import { Link, useNavigate } from 'react-router'
import { useCausalMap, useReview, useSummary } from '@/api/mypage'
import { OpenSourceNotice } from '@/components/OpenSourceNotice'
import { PageHeader } from '@/components/PageHeader'
import { AccountBar } from '@/pages/tab3/AccountBar'
import { isBaseEdge, learnedOf } from '@/pages/tab3/causalMapLayout'
import { ReviewList } from '@/pages/tab3/ReviewList'
import type { CausalMap, Summary } from '@/types/causalMap'

/**
 * 탭3 마이페이지 홈 (시안 26): 연속 학습 → 숫자 3개 → 나의 인과 지도 카드 → 다시 보는 개념.
 * 숫자는 마이페이지 API(summary·map·review)가 준 값만 쓴다. 인과 지도는 /mypage/map (시안 27).
 */
export const MyPage = () => {
  const navigate = useNavigate()
  const summary = useSummary()
  const map = useCausalMap()
  const review = useReview()

  return (
    <div className="h-full overflow-y-auto pb-6">
      <PageHeader />
      <div className="px-5">
        <AccountBar />
        <h2 className="text-2xl leading-snug font-bold text-slate-900">
          {summary.data?.studiedToday ? (
            <>
              오늘도 한 걸음
              <br />
              성장했어요
            </>
          ) : (
            <>
              오늘도 한 걸음
              <br />
              나아가 볼까요?
            </>
          )}
        </h2>

        {summary.isError && (
          <p className="mt-4 text-sm text-slate-500">학습 기록을 불러오지 못했어요</p>
        )}
        {summary.data && <SummaryBlock summary={summary.data} />}

        {map.isError && (
          <p className="mt-4 text-sm text-slate-500">인과 지도를 불러오지 못했어요</p>
        )}
        {map.data && <MapCard map={map.data} />}

        {review.isError && (
          <p className="mt-4 text-sm text-slate-500">다시 보는 개념을 불러오지 못했어요</p>
        )}
        {review.data && (
          <ReviewList
            concepts={review.data.concepts}
            onOpen={(id) => void navigate(`/mypage/map?focus=${encodeURIComponent(id)}`)}
          />
        )}

        {(summary.isPending || map.isPending || review.isPending) && (
          <p className="mt-4 text-sm text-slate-500">불러오는 중</p>
        )}

        <OpenSourceNotice />
      </div>
    </div>
  )
}

const SummaryBlock = ({ summary }: { summary: Summary }) => {
  const stats = [
    { label: '개념 학습', value: `${summary.conceptCount}개` },
    {
      label: '종합 정답률',
      value: summary.accuracy === null ? '-' : `${Math.round(summary.accuracy * 100)}%`,
    },
    { label: '판단 시뮬레이션', value: `${summary.judgementCount}회` },
  ]
  return (
    <>
      <p className="mt-5 rounded-2xl bg-blue-50 px-4 py-4 text-sm font-bold text-blue-700">
        {summary.streakDays > 0
          ? `${summary.streakDays}일 연속 학습 중이에요`
          : '오늘 첫 문제를 풀고 연속 학습을 시작해 보세요'}
      </p>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {stats.map((s) => (
          <div key={s.label} className="rounded-2xl bg-blue-50 px-3 py-3.5">
            <p className="text-[11px] text-slate-500">{s.label}</p>
            <p className="mt-1.5 text-2xl font-bold text-blue-700">{s.value}</p>
          </div>
        ))}
      </div>
    </>
  )
}

/** 나의 인과 지도 요약 카드. 개수는 지도 첫 화면 기준(배운 개념, 같은 테마 안 연결) */
const MapCard = ({ map }: { map: CausalMap }) => {
  const learned = learnedOf(map)
  const byId = new Map(map.nodes.map((n) => [n.id, n]))
  const edgeCount = map.edges.filter((e) => isBaseEdge(e, byId)).length

  return (
    <section className="mt-5 rounded-3xl bg-slate-900 p-5 text-white">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-lg font-bold">나의 인과 지도</h2>
        <p className="shrink-0 text-xs text-slate-400">
          개념 {learned.length}개 · 연결 {edgeCount}개
        </p>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-slate-300">
        {learned.length > 0
          ? '배운 뼈대가 마인드맵처럼 쌓여요. 개념을 누르면 다른 테마로 이어지는 연결도 보여요.'
          : '탭 1에서 뉴스 문제를 풀면 배운 개념이 여기에 쌓여요.'}
      </p>
      {learned.length > 0 && (
        <Link to="/mypage/map" className="mt-4 inline-block text-sm font-bold text-blue-300">
          지도 열기 ›
        </Link>
      )}
    </section>
  )
}
