import { Link, useParams } from 'react-router'

/** 카드뉴스 → 단계형 학습 화면 자리. 2주차에 목 데이터로 채운다. */
export const CardNewsPage = () => {
  const { cardId } = useParams()

  return (
    <div className="p-5">
      <Link to="/" className="text-primary text-sm">
        ← 뉴스 홈
      </Link>
      <p className="mt-6 text-sm text-slate-500">카드뉴스 화면 준비 중 ({cardId})</p>
    </div>
  )
}
