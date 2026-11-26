import { useSummary } from '@/api/mypage'
import { BackButton, CloseLink } from '@/pages/tab1/CloseLink'

interface LessonTopProps {
  /** 카드뉴스 첫 장부터 마지막 학습 단계까지 중 지금 어디인지 (0~100) */
  progress: number
  /** 있으면 닫기 옆에 뒤로 버튼을 둔다 */
  onBack?: () => void
  backLabel?: string
  /** 닫기를 누르면 갈 곳과 그 설명. 기본은 뉴스 홈 */
  closeTo?: string
  closeLabel?: string
}

/**
 * 카드뉴스·학습·결과 화면 맨 위 줄 (UI 시안 app.html 의 .l-top):
 * 닫기 · (뒤로) · 진행 막대 · 연속 학습 일수.
 * 연속 학습 일수는 서버가 센 값(마이페이지와 같은 summary)을 그대로 보여 주고, 못 받으면 숨긴다.
 */
export const LessonTop = ({
  progress,
  onBack,
  backLabel = '뒤로',
  closeTo,
  closeLabel,
}: LessonTopProps) => {
  const streak = useSummary().data?.streakDays
  const value = Math.round(Math.min(Math.max(progress, 0), 100))

  return (
    <div className="mm-l-top">
      <CloseLink to={closeTo} label={closeLabel} />
      {onBack && <BackButton onClick={onBack} label={backLabel} />}
      <div
        className="mm-bar"
        role="progressbar"
        aria-label="학습 진행"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
      >
        <i style={{ width: `${value}%` }} />
      </div>
      {streak !== undefined && (
        <span className="mm-flame" aria-label={`연속 학습 ${streak}일`}>
          <svg width="16" height="18" viewBox="0 0 16 18" aria-hidden>
            <path
              d="M8 1c1 3 5 5 5 9.5A5 5 0 0 1 3 10.5C3 8.5 4 7.5 5 6c.5 1.5 1.5 2 1.5 2C6.5 5.5 7 3 8 1z"
              fill="var(--color-butter)"
              stroke="var(--color-butter-ink)"
              strokeWidth="1.2"
              strokeLinejoin="round"
            />
          </svg>
          {streak}
        </span>
      )}
    </div>
  )
}
