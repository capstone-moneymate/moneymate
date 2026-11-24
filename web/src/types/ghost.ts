/**
 * 고스트 비교 (추가 구현 2-6) = GET /api/answers/ghost 응답 (docs/modules/ghost.md).
 * 같은 카드를 다시 풀었을 때 지난번 기록과 이번 기록. 숫자와 "좋아졌다" 판단은 모두 서버가 정한다.
 */
import type { Step } from '@/types/card'

type AnswerKind = Exclude<Step['kind'], 'concept'>

/** 한 단계의 기록. seconds 는 보이는 초(반올림), 판단해보기는 score 만 있다 */
export interface GhostCell {
  isCorrect: boolean | null
  seconds: number | null
  score: number | null
}

/** 끝까지 푼 시도 하나 */
export interface GhostAttempt {
  attemptNo: number
  /** 그 시도를 시작한 날 (yyyy-MM-dd, KST) */
  date: string
  /** "확실해요"라고 하고 틀린 답 수. 확신 기록이 없는 시도면 null */
  sureWrong: number | null
  steps: { stepId: string; kind: AnswerKind; record: GhostCell | null }[]
}

export interface GhostRow {
  stepId: string
  kind: AnswerKind
  previous: GhostCell | null
  /** 이번에 안 낸 단계는 null */
  current: GhostCell | null
  improved: boolean
  /** 최고 기록 경신 (이전 기록이 2번 이상 있을 때만 따진다) */
  best: boolean
}

export interface GhostComparison {
  previous: Pick<GhostAttempt, 'attemptNo' | 'date' | 'sureWrong'>
  current: Pick<GhostAttempt, 'attemptNo' | 'date' | 'sureWrong'>
  rows: GhostRow[]
  improvedSteps: number
}

export interface GhostReport {
  /** 끝까지 푼 시도 중 가장 최근. 다시 푸는 도중 "지난번엔 맞혔어요"에 쓴다 */
  lastComplete: GhostAttempt | null
  /** 가장 최근 시도와 그 앞의 끝까지 푼 시도 비교. 앞 시도가 없으면 null */
  comparison: GhostComparison | null
}
