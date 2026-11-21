import type { CalendarCard, StudyCalendar } from '@/types/causalMap'

/**
 * 학습 달력 목 데이터 (가짜 값). 날짜는 오늘(KST)에서 며칠 전으로 만들어 언제 열어도 이번 달에 표시가 보인다.
 * 카드 id 는 cardDetail 목에 있는 것만 써서 눌렀을 때 카드뉴스·퀴즈가 열린다.
 */
const kstDate = (daysAgo: number): string => {
  const d = new Date(Date.now() + 9 * 3600_000 - daysAgo * 86_400_000)
  return d.toISOString().slice(0, 10)
}

const rateHold = (daysAgo: number, correct: number): CalendarCard => ({
  cardId: 'mock-rate-hold',
  title: '한국은행, 기준금리 4연속 동결',
  cardDate: kstDate(daysAgo),
  stepCount: 4,
  answered: 4,
  graded: 4,
  correct,
})

const hbm = (daysAgo: number, answered: number, correct: number): CalendarCard => ({
  cardId: 'mock-hbm4',
  title: 'SK하이닉스, HBM 단일판매·공급계약 체결',
  cardDate: kstDate(daysAgo),
  stepCount: 1,
  answered,
  graded: answered,
  correct,
})

const kospi = (daysAgo: number, correct: number): CalendarCard => ({
  cardId: 'mock-kospi-3up',
  title: '코스피, 3거래일 연속 상승 마감',
  cardDate: kstDate(daysAgo),
  stepCount: 3,
  answered: 3,
  graded: 3,
  correct,
})

export const calendarMock: StudyCalendar = {
  days: [
    { date: kstDate(0), cards: [kospi(0, 2)] },
    { date: kstDate(1), cards: [rateHold(1, 3), hbm(3, 1, 1)] },
    { date: kstDate(2), cards: [hbm(2, 1, 0)] },
    { date: kstDate(5), cards: [rateHold(5, 4)] },
    { date: kstDate(6), cards: [kospi(6, 1)] },
    { date: kstDate(9), cards: [rateHold(9, 2), kospi(9, 3)] },
    { date: kstDate(15), cards: [hbm(15, 1, 1)] },
    { date: kstDate(32), cards: [kospi(32, 2)] },
  ],
}
