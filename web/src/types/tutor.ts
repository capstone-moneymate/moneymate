/**
 * 개념 단계 튜터 (server tutor 패키지 → 채점 서버 /tutor, docs/modules/tutor_server_api.md).
 * 이벤트 안의 키는 채점 서버 그대로(snake_case: guess_p)다.
 */

/** 화면 A(보기 고르기) 4종류 + 화면 B(칩을 칸에 넣기) 3종류 (추가구현_계획 1-3) */
export type TutorChoiceKind = '용어 뜻' | '헷갈리는 쌍' | '틀린 설명' | 'O/X'
export type TutorChipKind = '칩 빈칸' | '짝 맞추기' | '사례 분류'
export type TutorQuizKind = TutorChoiceKind | TutorChipKind

export const CHOICE_KINDS: readonly TutorQuizKind[] = ['용어 뜻', '헷갈리는 쌍', '틀린 설명', 'O/X']

/** 보기 고르기. O/X 는 question 대신 statement, options 는 ["O", "X"] */
export interface ChoiceContent {
  question?: string
  statement?: string
  options: string[]
}
/** 칩 빈칸: sentence 의 ___ 두 곳에 chips 4개 중 2개 */
export interface ChipBlankContent {
  sentence: string
  chips: string[]
}
/** 짝 맞추기: 용어마다 뜻 하나. meanings 는 용어 순서 그대로 오므로 화면이 섞어 보여 준다 */
export interface MatchContent {
  terms: string[]
  meanings: string[]
}
/** 사례 분류: 사례 4개를 바구니 2개로 */
export interface SortContent {
  baskets: string[]
  cases: string[]
}

export type TutorQuizEvent =
  | {
      type: 'quiz'
      kind: TutorChoiceKind
      concept: string
      content: ChoiceContent
      guess_p: number
    }
  | { type: 'quiz'; kind: '칩 빈칸'; concept: string; content: ChipBlankContent; guess_p: number }
  | { type: 'quiz'; kind: '짝 맞추기'; concept: string; content: MatchContent; guess_p: number }
  | { type: 'quiz'; kind: '사례 분류'; concept: string; content: SortContent; guess_p: number }

/** 답한 뒤 채점. key 는 정답 (보기 번호, 또는 칸 순서대로 칩·뜻·바구니 번호) */
export interface TutorGradedEvent {
  type: 'graded'
  concept: string
  kind: TutorQuizKind
  correct: boolean
  key: number | number[]
  explanation: string
}

/** 설명. 정의·보충·예시 칸이 따로 온다. example 은 빈 문자열일 수 있다 (그러면 "예를 들면" 상자를 숨긴다) */
export interface TutorExplainEvent {
  type: 'explain'
  concept: string
  definition: string
  detail: string
  example: string
}

export interface TutorDoneEvent {
  type: 'done'
  /** go_main / quiz_limit / turn_limit / no_targets / stop:… */
  by: string
}

export type TutorEvent = TutorExplainEvent | TutorQuizEvent | TutorGradedEvent | TutorDoneEvent

export interface TutorState {
  sessionId: string
  status: 'waiting' | 'running' | 'done' | 'error'
  finishedBy: string | null
  /** 이 카드의 목표 개념 */
  targets: string[]
  quizzes: number
  maxQuizzes: number
  /** start·answer 는 이번 요청에서 새로 생긴 이벤트만, GET 은 전부 */
  events: TutorEvent[]
}

/** 보기 고르기는 번호 하나, 칩을 칸에 넣기는 칸 순서대로 번호 목록 */
export type TutorAnswer = number | number[]
