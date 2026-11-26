import { ReactFlowProvider } from '@xyflow/react'
import { Link, useSearchParams } from 'react-router'
import { useLogout, useMe } from '@/api/auth'
import { useCalibration, useReviews } from '@/api/learner'
import { useCalendar, useCausalMap, useSummary } from '@/api/mypage'
import { Mate } from '@/components/Mate'
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
    <div className="h-full overflow-y-auto pb-6">
      <ProfileHeader streakDays={summary.data?.streakDays ?? null} cardCount={cardCount} />

      <div role="tablist" aria-label="기록 보기 전환" className="mm-subtabs">
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

      <div className="pt-4">
        {view === 'calendar' ? (
          <>
            {calendar.isPending && (
              <p className="text-sub px-5 text-sm font-semibold">불러오는 중</p>
            )}
            {calendar.isError && (
              <p className="text-sub px-5 text-sm font-semibold">학습 달력을 불러오지 못했어요</p>
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

/** 프로필 줄 (UI 시안 app.html 의 .me-head): 마스코트 얼굴 · 닉네임 님 · 연속 학습 · 푼 카드뉴스 수 · 로그인/로그아웃 */
const ProfileHeader = ({
  streakDays,
  cardCount,
}: {
  streakDays: number | null
  cardCount: number | null
}) => {
  const me = useMe()
  const logout = useLogout()

  return (
    <header className="flex items-center gap-3 px-5 pt-[calc(14px+env(safe-area-inset-top))] pb-3">
      <div className="border-blue bg-blue-soft grid size-[62px] shrink-0 place-items-center overflow-hidden rounded-full border-[3px]">
        <Mate className="size-[52px]" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[21px] font-extrabold tracking-[-0.02em]">
          {me.data ? `${me.data.loginId} 님` : '둘러보는 중'}
        </p>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          <span className="mm-chip butter h-[30px] text-[13px]">
            연속 학습 {streakDays ?? '-'}일
          </span>
          <span className="mm-chip line h-[30px] text-[13px]">카드뉴스 {cardCount ?? '-'}장</span>
        </div>
      </div>
      {me.data ? (
        <button
          type="button"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          className="text-faint shrink-0 px-1 py-2 text-[12.5px] font-bold underline underline-offset-[3px]"
        >
          로그아웃
        </button>
      ) : (
        !me.isPending && (
          <Link
            to="/login?next=/mypage"
            className="text-blue-ink shrink-0 px-1 py-2 text-[12.5px] font-bold underline underline-offset-[3px]"
          >
            로그인하기
          </Link>
        )
      )}
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
  <button type="button" role="tab" aria-selected={active} onClick={onClick}>
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
      {reviews.isPending && <p className="text-sub text-sm font-semibold">불러오는 중</p>}
      {reviews.isError && (
        <p className="text-sub text-sm font-semibold">오늘의 복습을 불러오지 못했어요</p>
      )}
      {reviews.data && <ReviewQueueCard queue={reviews.data} />}
      {calibration.isError && (
        <p className="text-sub text-sm font-semibold">확신 점검을 불러오지 못했어요</p>
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
      {isPending && <p className="text-sub text-sm font-semibold">불러오는 중</p>}
      {isError && <p className="text-sub text-sm font-semibold">인과 지도를 불러오지 못했어요</p>}
      {data && !hasLearned && (
        <div className="mm-empty">
          <Mate mood="think" />
          <p>
            아직 배운 개념이 없어요.
            <br />
            뉴스 한 건을 배우면 원인과 결과가 여기에 이어져요.
          </p>
          <Link to="/" className="mm-btn">
            오늘 뉴스 배우러 가기
          </Link>
        </div>
      )}
      {data && hasLearned && (
        <div className="mm-box flex h-[480px] flex-col overflow-hidden rounded-[22px]">
          <ReactFlowProvider>
            <CausalMapView map={data} />
          </ReactFlowProvider>
        </div>
      )}
    </section>
  )
}

const CalendarIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden>
    <rect x="3" y="5" width="18" height="16" rx="3" />
    <path d="M3 10h18M8 3v4M16 3v4" />
  </svg>
)

const ShareIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden>
    <circle cx="18" cy="5" r="3" />
    <circle cx="6" cy="12" r="3" />
    <circle cx="18" cy="19" r="3" />
    <path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4" />
  </svg>
)

const GaugeIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden>
    <path d="M4 18a8 8 0 1 1 16 0" />
    <path d="m12 18 4-6" />
  </svg>
)
