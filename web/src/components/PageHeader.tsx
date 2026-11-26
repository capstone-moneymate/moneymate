import { Mate } from '@/components/Mate'

/** 탭 공통 상단 헤더: 마스코트 + MONEYMATE 워드마크 (UI 시안 app.html 의 .home-head) */
export const PageHeader = () => {
  return (
    <header className="flex items-center gap-2 px-5 pt-[calc(12px+env(safe-area-inset-top))] pb-2.5">
      <Mate className="size-[34px]" />
      <h1 className="mm-wordmark text-[21px]">MONEYMATE</h1>
    </header>
  )
}
