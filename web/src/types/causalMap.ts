/**
 * 탭3 마이페이지 타입. 마이페이지 API(B, server mypage 패키지 MypageDtos)의 응답 모양과 같은 이름이다.
 * - GET /api/mypage/map?userId=...    인과 지도 (CausalMap)
 * - GET /api/mypage/review?userId=... 다시 보는 개념 (Review)
 * - GET /api/mypage/summary?userId=... 홈 숫자 (Summary)
 * 인과 지도 = 이 사용자가 배운 개념 + 거기서 한 걸음 뻗은 사전 연결 (docs/modules/mypage_api.md).
 */

/** 연결의 힘 방향 ← causal_edges.force_dir. up: 올리는 힘, down: 누르는 힘 */
export type ForceDir = 'up' | 'down'

/** 지도에 놓이는 개념 하나 */
export interface MapNode {
  /** ← concepts.id */
  id: string
  /** ← concepts.name */
  name: string
  /** 테마(금리, AI·반도체, 차트 읽기 …) ← concepts.theme. 접기 단위 */
  theme: string
  /** 맞힌 횟수 ← user_concepts.correct */
  correct: number
  /** 푼 횟수 ← user_concepts.total */
  total: number
  /** true = 내가 배운 개념(total > 0). false = 배운 개념과 연결된 아직 안 배운 개념(correct·total 0) */
  learned: boolean
}

/** 개념 사이 연결 하나 (from 이 to 를 올리거나 누른다) */
export interface MapEdge {
  /** ← causal_edges.from_concept */
  from: string
  /** ← causal_edges.to_concept */
  to: string
  forceDir: ForceDir
}

export interface CausalMap {
  nodes: MapNode[]
  edges: MapEdge[]
}

/** 다시 보는 개념 하나 */
export interface ReviewConcept {
  id: string
  name: string
  theme: string
  correct: number
  total: number
  /** correct / total 소수 (0.5 = 50%). 서버가 계산해 주고 반올림하지 않는다. 화면은 % 표기만 */
  accuracy: number
}

/** 정답률 낮은 순 → 푼 횟수 적은 순 → id 순 (서버가 정렬, 화면은 그대로 쓴다) */
export interface Review {
  concepts: ReviewConcept[]
}

/** 마이페이지 홈 위쪽 숫자. 계산은 서버가 하고 화면은 표기만 한다 */
export interface Summary {
  /** 연속 학습 일수 (KST). 오늘 아직 안 풀었으면 어제까지 이어진 날수 */
  streakDays: number
  /** 오늘(KST) 답안을 냈는가 */
  studiedToday: boolean
  /** 배운 개념 수 */
  conceptCount: number
  /** 종합 정답률 소수 (객관식 정답 + 판단해보기 60점 이상) / 채점된 답안. 채점된 답안이 없으면 null */
  accuracy: number | null
  /** 채점된 답안 수 */
  gradedCount: number
  /** 판단해보기 제출 수 */
  judgementCount: number
}

/** 학습 달력의 카드 하나. 숫자는 그날 마지막으로 낸 답안 기준 (서버가 센 값) */
export interface CalendarCard {
  cardId: string
  title: string
  /** 카드가 노출된 날 (yyyy-MM-dd). 지난 뉴스를 풀었으면 푼 날과 다르다 */
  cardDate: string
  /** 문제 수 (개념 설명 단계 제외) */
  stepCount: number
  /** 그날 답한 문제 수 */
  answered: number
  /** 채점된 문제 수 */
  graded: number
  /** 맞은 문제 수 */
  correct: number
}

/** 문제를 푼 하루 (KST yyyy-MM-dd). 카드는 그날 처음 푼 순서 */
export interface CalendarDay {
  date: string
  cards: CalendarCard[]
}

/** GET /api/mypage/calendar. 최근 400일, 최근 날짜 먼저 */
export interface StudyCalendar {
  days: CalendarDay[]
}
