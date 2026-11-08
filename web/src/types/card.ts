/**
 * 탭1 카드뉴스·단계형 학습에서 쓰는 타입. 서버 카드 API(Spring Boot) 응답도 이 모양에 맞춘다.
 * "← "는 서버가 값을 가져올 테이블·컬럼이다. 정답(steps.answer)은 서버가 내려보내지 않는다.
 */
import type { CardType } from '@/types/news'

/** 카드뉴스 한 장 ← cards.slides[i] */
export interface Slide {
  /** "무슨 일이 있었나요?" / "시장이 주목한 포인트" / "오늘의 결론" */
  label: string
  heading: string
  body: string
  /** 코드가 계산한 숫자 칸 (선택). 예: { label: '기준금리', value: '3.00%' } */
  facts?: { label: string; value: string }[]
}

interface StepBase {
  /** ← steps.id */
  id: string
  /** ← steps.step_no */
  no: number
  /** 이 단계가 다루는 개념 id. causal_order 는 경로 순서 그대로 (B와 합의) */
  conceptIds: string[]
}

/** 개념 학습 */
export interface ConceptStep extends StepBase {
  kind: 'concept'
  title: string
  body: string
  terms: { term: string; desc: string }[]
}

/** 간단 퀴즈 (객관식, 코드 채점) */
export interface QuizStep extends StepBase {
  kind: 'quiz'
  question: string
  options: string[]
}

/** 인과 순서 (사전 경로와 비교, 코드 채점). items 는 섞인 순서로 내려온다 */
export interface CausalOrderStep extends StepBase {
  kind: 'causal_order'
  question: string
  items: { conceptId: string; label: string }[]
}

/** 차트 읽기 (B 담당 ChartStep.tsx 가 그린다) */
export interface ChartStep extends StepBase {
  kind: 'chart'
  question: string
  ticker: string
  options: string[]
}

/**
 * 판단해보기 (모든 유형 공통, 마지막 단계). 선택 + 근거(필수).
 * 선택은 채점하지 않고 근거만 루브릭 채점 (A의 /api/judgement).
 * AI 분석은 단계가 아니라 제출 후 결과 화면에 나온다 (003: steps.kind 5종)
 */
export interface JudgementStep extends StepBase {
  kind: 'judgement'
  question: string
  context: string
  choices: string[]
}

export type Step = ConceptStep | QuizStep | CausalOrderStep | ChartStep | JudgementStep

export interface CardDetail {
  id: string
  type: CardType
  title: string
  theme: string | null
  sourceName: string
  sourceUrl: string
  sourcePublishedAt: string
  /** 유형 3 연결 종목 ← cards.ticker */
  ticker: string | null
  slides: Slide[]
  steps: Step[]
}

/** 사용자가 낸 답 */
export type AnswerInput =
  | { kind: 'quiz' | 'chart'; optionIndex: number }
  | { kind: 'causal_order'; order: string[] }
  /** choice: 고른 선택지 문장 (채점하지 않고 저장만), reason: 근거 (채점 대상) */
  | { kind: 'judgement'; choiceIndex: number; choice: string; reason: string }

/** 루브릭 기준별 점수 (증거 0~2 · 추론 0~4 · 반박 0~3, 9점 → 100점 환산) */
export interface Rubric {
  evidence: number
  reasoning: number
  rebuttal: number
}

/** AI 분석 피드백 (A #56). 인과 뼈대는 카드의 chain 순서, used = 근거에 그 개념을 썼는지 */
export interface JudgementFeedback {
  good: string
  thinkMore: string
  chain: { name: string; used: boolean }[]
  chainComment: string
}

/**
 * 판단해보기 채점 결과 = A의 POST /api/judgement 응답 (docs/modules/judgement_api.md).
 * 채점 서버가 실패하면 score·correct·rubric·feedback 이 null 이고 message(고정 문구)만 온다.
 */
export interface JudgementGrade {
  /** 100점 환산. 채점하지 못했으면 null */
  score: number | null
  /** 60점 이상이면 true (conventions P17) */
  correct: boolean | null
  rubric: Rubric | null
  /** Claude 채점 이유 {reasoning, rebuttal}. 규칙 채점이면 빈 객체 */
  reasons: Partial<Record<'reasoning' | 'rebuttal', string>>
  grader: 'claude' | 'rule' | null
  /** 같은 답안의 이전 채점 결과를 다시 쓴 경우 */
  reused: boolean
  /** 채점하지 못했을 때 보여 줄 고정 문구 */
  message: string | null
  feedback: JudgementFeedback | null
}

/** 채점 결과. 코드 채점(퀴즈·순서·차트)은 isCorrect, 루브릭 채점(판단·주관식)은 grade */
export interface AnswerResult {
  stepId: string
  isCorrect: boolean | null
  /** 해설 (코드 채점 단계) */
  explanation?: string
  /** 정답 보기 번호 또는 순서 (틀렸을 때 보여 줌) */
  correct?: number | string[]
  grade?: JudgementGrade
}
