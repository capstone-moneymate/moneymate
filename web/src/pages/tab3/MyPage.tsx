import { ReactFlowProvider } from '@xyflow/react'
import { Link, useSearchParams } from 'react-router'
import { useLogout, useMe } from '@/api/auth'
import { useCalibration, useReviews } from '@/api/learner'
import { useCalendar, useCausalMap, useSummary } from '@/api/mypage'
import { OpenSourceNotice } from '@/components/OpenSourceNotice'
import { CausalMapView } from '@/pages/tab3/CausalMapView'
import { ConfidenceCard } from '@/pages/tab3/ConfidenceCard'
import { ReviewQueueCard } from '@/pages/tab3/ReviewQueueCard'
import { StudyCalendar } from '@/pages/tab3/StudyCalendar'

type View = 'calendar' | 'learn' | 'map'

/**
 * 탭3 마이페이지 (2026-11-21 시안 tab3_01·02). 위: 프로필(닉네임·연속 학습·푼 카드뉴스 수),
 * 가운데 탭: 달력(문제를 푼 날 표시, 누르면 그날 카드뉴스·퀴즈 다시 보기) / 내 학습(오늘의 복습·확신 점검,
 * 추가 구현 2-7) / 인과 지도. 고른 탭은 ?view=learn, ?view=map 으로 주소에 남겨 뒤로 가기로 돌아와도 그대로다.
 */
export const MyPage = () => {
  const [params, setParams] = useSearchParams()
  const viewParam = params.get('view')
  const view: View = viewParam === 'map' || viewParam === 'learn' ? viewParam : 'calendar'
  const summary = useSummary()
  const calendar = useCalendar()

  const cardCount = calendar.data
    ? new Set(calendar.data.days.flatMap((d) => d.cards.map((c) => c.cardId))).size
    : null

  return (
    <div className="h-full overflow-y-auto bg-[#f0f3fc] pb-6">
      <ProfileHeader streakDays={summary.data?.streakDays ?? null} cardCount={cardCount} />

      <div role="tablist" className="grid grid-cols-3 border-y border-[#dfe4f6] bg-white">
        <TabButton
          active={view === 'calendar'}
          label="달력"
          icon={<CalendarIcon />}
          onClick={() => setParams({}, { replace: true })}
        />
        <TabButton
          active={view === 'learn'}
          label="내 학습"
          icon={<GaugeIcon />}
          onClick={() => setParams({ view: 'learn' }, { replace: true })}
        />
        <TabButton
          active={view === 'map'}
          label="인과 지도"
          icon={<ShareIcon />}
          onClick={() => setParams({ view: 'map' }, { replace: true })}
        />
      </div>

      <div className="pt-6">
        {view === 'calendar' ? (
          <>
            {calendar.isPending && <p className="px-5 text-sm text-slate-500">불러오는 중</p>}
            {calendar.isError && (
              <p className="px-5 text-sm text-slate-500">학습 달력을 불러오지 못했어요</p>
            )}
            {calendar.data && (
              <StudyCalendar days={calendar.data.days} streakDays={summary.data?.streakDays ?? 0} />
            )}
          </>
        ) : view === 'learn' ? (
          <LearnPanel />
        ) : (
          <MapPanel />
        )}
        <div className="px-5">
          <OpenSourceNotice />
        </div>
      </div>
    </div>
  )
}

/** 프로필 줄: 동그란 얼굴 · 닉네임 님 · 연속 학습 · 푼 카드뉴스 수. 로그인·로그아웃은 오른쪽 위 작은 글자 */
const ProfileHeader = ({
  streakDays,
  cardCount,
}: {
  streakDays: number | null
  cardCount: number | null
}) => {
  const me = useMe()
  const logout = useLogout()
  const name = me.data?.loginId ?? '게스트'

  return (
    <header className="flex items-center gap-4 px-5 pt-6 pb-5">
      <div className="flex size-16 shrink-0 items-center justify-center rounded-full border-[3px] border-[#5468b8] bg-[#cfe9fb] text-2xl font-bold text-[#3a4a99]">
        {name.slice(0, 1).toUpperCase()}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <p className="truncate text-xl font-bold text-[#232c5c]">{name} 님</p>
          {me.data ? (
            <button
              type="button"
              onClick={() => logout.mutate()}
              disabled={logout.isPending}
              className="shrink-0 text-xs font-semibold text-[#5b6694]"
            >
              로그아웃
            </button>
          ) : (
            !me.isPending && (
              <Link
                to="/login?next=/mypage"
                className="shrink-0 text-xs font-semibold text-[#5468b8]"
              >
                로그인
              </Link>
            )
          )}
        </div>
        <div className="mt-2 flex flex-wrap gap-2 text-sm font-bold">
          <span className="rounded-full bg-[#ffd84d] px-3.5 py-1.5 text-[#232c5c]">
            🔥 연속 학습 {streakDays ?? '-'}일
          </span>
          <span className="rounded-full border-2 border-[#dfe4f6] bg-white px-3.5 py-1 text-[#3a4473]">
            카드뉴스 {cardCount ?? '-'}장
          </span>
        </div>
      </div>
    </header>
  )
}

interface TabButtonProps {
  active: boolean
  label: string
  icon: React.ReactNode
  onClick: () => void
}

const TabButton = ({ active, label, icon, onClick }: TabButtonProps) => (
  <button
    type="button"
    role="tab"
    aria-selected={active}
    onClick={onClick}
    className={`flex flex-col items-center gap-1 border-b-4 pt-3 pb-2 text-sm font-bold ${
      active ? 'border-[#5468b8] text-[#3a4a99]' : 'border-transparent text-[#5b6694]'
    }`}
  >
    {icon}
    {label}
  </button>
)

/** 내 학습 탭: 오늘의 복습(FSRS 복습 목록)과 확신 점검(2 × 2 표). 둘은 따로 불러와서 한쪽이 실패해도 다른 쪽은 보인다 */
const LearnPanel = () => {
  const reviews = useReviews()
  const calibration = useCalibration()

  return (
    <div className="space-y-5 px-5">
      {reviews.isPending && <p className="text-sm text-slate-500">불러오는 중</p>}
      {reviews.isError && <p className="text-sm text-slate-500">오늘의 복습을 불러오지 못했어요</p>}
      {reviews.data && <ReviewQueueCard queue={reviews.data} />}
      {calibration.isError && (
        <p className="text-sm text-slate-500">확신 점검을 불러오지 못했어요</p>
      )}
      {calibration.data && <ConfidenceCard calibration={calibration.data} />}
    </div>
  )
}

/** 인과 지도 탭. 지도 자체(범례·접고 펴기·개념 고르기)는 /mypage/map 과 같은 CausalMapView */
const MapPanel = () => {
  const { data, isPending, isError } = useCausalMap()
  const hasLearned = !!data?.nodes.some((n) => n.learned)

  return (
    <section className="px-5">
      {isPending && <p className="text-sm text-slate-500">불러오는 중</p>}
      {isError && <p className="text-sm text-slate-500">인과 지도를 불러오지 못했어요</p>}
      {data && !hasLearned && (
        <div className="rounded-3xl bg-white px-5 py-10 text-center">
          <p className="text-sm font-semibold text-[#232c5c]">아직 배운 개념이 없어요</p>
          <p className="mt-1 text-xs text-[#5b6694]">
            탭 1에서 뉴스 문제를 풀면 배운 개념이 지도에 쌓여요
          </p>
        </div>
      )}
      {data && hasLearned && (
        <div className="flex h-[480px] flex-col overflow-hidden rounded-[28px] bg-white shadow-[0_6px_0_#dfe4f6]">
          <ReactFlowProvider>
            <CausalMapView map={data} />
          </ReactFlowProvider>
        </div>
      )}
    </section>
  )
}

const CalendarIcon = () => (
  <svg
    width="26"
    height="26"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    aria-hidden
  >
    <rect x="3" y="5" width="18" height="16" rx="3" />
    <path d="M3 10h18M8 3v4M16 3v4" />
  </svg>
)

const ShareIcon = () => (
  <svg
    width="26"
    height="26"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    aria-hidden
  >
    <circle cx="18" cy="5" r="3" />
    <circle cx="6" cy="12" r="3" />
    <circle cx="18" cy="19" r="3" />
    <path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4" />
  </svg>
)

const GaugeIcon = () => (
  <svg
    width="26"
    height="26"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    aria-hidden
  >
    <path d="M4 18a8 8 0 1 1 16 0" />
    <path d="m12 18 4-6" />
  </svg>
)
