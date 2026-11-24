/**
 * 학습자 상태 조회 (GET /api/learner/*, docs/modules/learner_api.md). 숫자는 모두 서버(채점 서버)가 계산한 값이고
 * 화면은 표기만 한다.
 */

/** 오늘 복습할 개념 하나 */
export interface ReviewItem {
  nodeId: number
  /** 개념 이름 */
  concept: string
  /** 알 확률 (BKT, 0~1) */
  pKnow: number
  /** 지금 기억하고 있을 확률 (FSRS, 0~1) */
  retrievability: number
  /** sure_wrong = 확실해요라고 했는데 틀렸던 개념, due = 복습일이 됨 */
  reason: 'sure_wrong' | 'due'
  /** 복습일 (ISO 시각) */
  dueAt: string
}

/** GET /api/learner/reviews. items 는 앞에서부터 복습할 순서 */
export interface ReviewQueue {
  /** 하루 복습 개념 수 상한 */
  limit: number
  /** 오늘 이미 복습한 개념 수 */
  doneToday: number
  /** 복습일이 된 개념 전체 수 (상한에 잘리기 전) */
  dueTotal: number
  items: ReviewItem[]
}

/** 정답/오답 × 확실/헷갈려요 2 × 2 표 하나. 분모가 0 인 비율은 null */
export interface CalibrationSummary {
  total: number
  /** 답이 충분한가. false 면 비율을 보여 주지 않는다 */
  enough: boolean
  sureRight: number
  /** 확실해요인데 틀림 */
  sureWrong: number
  unsureRight: number
  unsureWrong: number
  /** 맞힌 답 중 확실해요 비율 */
  sensitivity: number | null
  /** 틀린 답 중 헷갈려요 비율 */
  specificity: number | null
  /** 틀린 답 중 확실해요 비율 */
  illusion: number | null
  /** 확실해요 답의 정답률 */
  sureAccuracy: number | null
  /** 헷갈려요 답의 정답률 */
  unsureAccuracy: number | null
  gap: number | null
  gamma: number | null
  /** 확실해요 비율 - 정답률. 양수면 과신 */
  bias: number | null
}

/** GET /api/learner/calibration */
export interface Calibration {
  all: CalibrationSummary
  /** 최근 recentDays 일 */
  recent: CalibrationSummary
  /** 그 전 */
  earlier: CalibrationSummary
  recentDays: number
  /** 확실해요라고 했는데 틀렸고 아직 다시 맞히지 못한 개념 이름 */
  sureWrongConcepts: string[]
}

/**
 * 복습 문제 종류 (worker/tutor/quiz.py 의 이름 그대로). 지금은 보기 고르기 네 가지만 낸다.
 * 헷갈리는 쌍은 헷갈리기 쉬운 이웃이 있는 개념에만 나오고, 보기는 두 개념 이름이다
 */
export type ReviewQuizKind = '용어 뜻' | '헷갈리는 쌍' | '틀린 설명' | 'O/X'

/** POST /api/learner/review/quiz. 정답과 해설은 들어 있지 않다 (답을 내면 ReviewResult 로 온다) */
export interface ReviewQuiz {
  quizId: number
  nodeId: number
  concept: string
  kind: ReviewQuizKind
  /** 보기 고르기는 question, O/X 는 statement 가 온다. options 는 고를 보기 */
  content: { question?: string; statement?: string; options: string[] }
  /** 찍어서 맞힐 확률 (서버 계산) */
  guessP: number
}

/** POST /api/learner/review/answer */
export interface ReviewResult {
  correct: boolean
  /** 정답 보기 번호 */
  key: number
  explanation: string
  concept: string
  /** 반영한 뒤의 알 확률 (BKT) */
  pKnow: number
  /** 다음 복습일 (ISO 시각) */
  dueAt: string
}
