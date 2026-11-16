import { ReactFlowProvider } from '@xyflow/react'
import { useNavigate } from 'react-router'
import { useCausalMap } from '@/api/mypage'
import { CausalMapView } from '@/pages/tab3/CausalMapView'

/**
 * 탭3 마이페이지: 나의 인과 지도 (React Flow 시험, 목 데이터). 다시 보는 개념은 다음 이슈.
 * 헤더는 디자인 시안대로 뒤로 가기 + 제목이라 공통 PageHeader(C 담당) 대신 이 화면 안에 둔다.
 */
export const MyPage = () => {
  const { data, isPending, isError } = useCausalMap()
  const navigate = useNavigate()

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-3 border-b border-slate-100 px-4 pt-5 pb-3">
        <button
          type="button"
          aria-label="뒤로 가기"
          onClick={() => void navigate(-1)}
          className="flex size-10 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-700"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden
          >
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
        <div>
          <h1 className="text-lg font-bold text-slate-900">나의 인과 지도</h1>
          <p className="text-xs text-slate-500">테마를 누르면 접고 펼 수 있어요</p>
        </div>
      </header>
      {isPending && <p className="px-5 pt-4 text-sm text-slate-500">불러오는 중</p>}
      {isError && <p className="px-5 pt-4 text-sm text-slate-500">인과 지도를 불러오지 못했어요</p>}
      {data && (
        <ReactFlowProvider>
          <CausalMapView map={data} />
        </ReactFlowProvider>
      )}
    </div>
  )
}
