/** 탭 공통 상단 헤더 (머니메이트 + 알림) */
export const PageHeader = () => {
  return (
    <header className="flex items-center justify-between px-5 pt-5 pb-3">
      <h1 className="text-xl font-bold text-slate-900">머니메이트</h1>
      <button
        type="button"
        aria-label="알림"
        className="flex size-10 items-center justify-center rounded-full bg-slate-100 text-slate-700"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          aria-hidden
        >
          <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
      </button>
    </header>
  )
}
