import { useSearchParams } from 'react-router'

/**
 * 탭3 "풀었던 내용 보기" 모드. 주소에 ?review=yyyy-MM-dd(KST, 푼 날)가 있으면 카드뉴스·학습·결과 화면이
 * 새로 풀지 않고 그날 낸 답과 채점 결과를 보여 준다. 없으면 평소처럼 처음부터 푼다.
 */
export const useReviewDate = (): string | null => {
  const [params] = useSearchParams()
  const value = params.get('review')
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : null
}

/** 다음 화면 주소에 review 를 이어 붙인다 */
export const withReview = (path: string, date: string | null): string =>
  date ? `${path}?review=${date}` : path

/** '2026-11-20' → '11월 20일' */
export const reviewLabel = (date: string): string => {
  const [, m, d] = date.split('-').map(Number)
  return `${m}월 ${d}일`
}
