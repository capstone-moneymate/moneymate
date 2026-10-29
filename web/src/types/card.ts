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

/** 판단해보기 (선택은 채점하지 않고 근거만 루브릭 채점, A의 /api/judgement) */
export interface JudgementStep extends StepBase {
  kind: 'judgement'
  question: string
  context: string
  choices: string[]
}

/** 주관식 (유형 3, 루브릭 채점) */
export interface OpenEndedStep extends StepBase {
  kind: 'open_ended'
  question: string
  context: string
}

/** AI 분석 (유형 3). 바로 앞 주관식의 채점 결과를 보여 주는 자리라 내용은 비어 있다 */
export interface AiAnalysisStep extends StepBase {
  kind: 'ai_analysis'
}

export type Step =
  | ConceptStep
  | QuizStep
  | CausalOrderStep
  | ChartStep
  | JudgementStep
  | OpenEndedStep
  | AiAnalysisStep

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
  | { kind: 'judgement'; choiceIndex: number; reason: string }
  | { kind: 'open_ended'; reason: string }

/** 루브릭 채점 결과 (증거 2 · 추론 3 · 반박 2 → 100점 환산) ← user_answers.rubric·score·feedback */
export interface RubricGrade {
  score: number
  rubric: { evidence: number; reasoning: number; rebuttal: number }
  feedback: {
    good: string
    consider: string
    /** 인과 뼈대 (개념 이름 순서) */
    skeleton: string[]
  }
}

/** 채점 결과. 코드 채점(퀴즈·순서·차트)은 isCorrect, 루브릭 채점(판단·주관식)은 grade */
export interface AnswerResult {
  stepId: string
  isCorrect: boolean | null
  /** 해설 (코드 채점 단계) */
  explanation?: string
  /** 정답 보기 번호 또는 순서 (틀렸을 때 보여 줌) */
  correct?: number | string[]
  grade?: RubricGrade
}
