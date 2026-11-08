import { DailyLimitError } from '@/api/client'
import { cardDetailMocks } from '@/api/mocks/cardDetail'
import type { JudgementGrade } from '@/types/card'

/**
 * 판단해보기 목 채점 (화면 확인용). 응답 모양은 A의 POST /api/judgement 와 같다.
 * 서버(Spring)가 develop 에 올라오면 VITE_USE_MOCK=false 로 실제 채점을 쓰고, 이 파일은 지운다.
 *
 * 개발 중(pnpm dev)에만 근거에 아래 말을 넣으면 서버의 예외 응답을 흉내 낸다.
 * - "#채점실패": 채점 서버 실패 → 점수 없이 고정 문구(message)
 * - "#한도": 하루 채점 횟수 초과(429)
 */

/** 목 카드의 개념 이름과 답안에서 찾을 표현 (db/seeds/concepts.csv 의 name·aliases 에서) */
const CONCEPTS: Record<string, { name: string; words: string[] }> = {
  rate_hold: { name: '기준금리 동결', words: ['동결', '금리 유지'] },
  bank_margin: { name: '은행 예대금리차(잔액 기준)', words: ['예대금리차', '예대마진'] },
  growth_valuation: { name: '성장주 가치평가', words: ['성장주', '기술주', '밸류에이션'] },
  hbm_supply: { name: 'HBM 공급 확대', words: ['HBM'] },
  gpu_demand: { name: 'AI 반도체 수요', words: ['GPU', 'AI 칩', '반도체 수요'] },
  ai_investment: { name: 'AI 데이터센터 투자', words: ['데이터센터', 'AI 투자', '설비투자'] },
  consecutive_rise: { name: '연속 상승', words: ['연속 상승', '연속'] },
  volume_spike: { name: '거래량 급증', words: ['거래량'] },
}

const FIXED_MESSAGE = '근거 있는 선택이었어요. 이런 경우도 생길 수 있어요.'

const conceptIdsOf = (stepId: string): string[] => {
  for (const card of Object.values(cardDetailMocks)) {
    const step = card.steps.find((s) => s.id === stepId)
    if (step) return step.conceptIds
  }
  return []
}

export const mockJudgement = async (stepId: string, reason: string): Promise<JudgementGrade> => {
  if (import.meta.env.DEV && reason.includes('#한도')) {
    throw new DailyLimitError('오늘 판단 채점은 30번까지 할 수 있어요. 내일 다시 해 주세요.')
  }
  if (import.meta.env.DEV && reason.includes('#채점실패')) {
    return {
      score: null,
      correct: null,
      rubric: null,
      reasons: {},
      grader: null,
      reused: false,
      message: FIXED_MESSAGE,
      feedback: null,
    }
  }

  // 근거에 숫자가 있으면 증거, 연결어 수만큼 추론, 반박어 수만큼 반박 (루브릭 9점 → 100점)
  const evidence = Math.min(2, (/\d/.test(reason) ? 1 : 0) + (reason.length >= 60 ? 1 : 0))
  const links = reason.match(/때문|그래서|따라서|이어|그러면|늘면|오르면|줄면/g)?.length ?? 0
  const reasoning = Math.min(4, links)
  const rebuttal = Math.min(3, reason.match(/다만|하지만|반대로|위험|그런데/g)?.length ?? 0)
  const score = Math.round(((evidence + reasoning + rebuttal) / 9) * 100)

  const chain = conceptIdsOf(stepId)
    .filter((id) => CONCEPTS[id])
    .map((id) => ({
      name: CONCEPTS[id].name,
      used: CONCEPTS[id].words.some((w) => reason.includes(w)),
    }))
  const missing = chain.filter((c) => !c.used).map((c) => c.name)

  return {
    score,
    correct: score >= 60,
    rubric: { evidence, reasoning, rebuttal },
    reasons: {
      reasoning:
        reasoning > 0
          ? '개념을 이어서 판단까지 연결했어요.'
          : '개념 사이의 연결이 아직 보이지 않아요.',
      rebuttal:
        rebuttal > 0
          ? '판단을 뒤집을 수 있는 요인을 고려했어요.'
          : '다른 힘이나 위험은 아직 적지 않았어요.',
    },
    grader: 'claude',
    reused: false,
    message: null,
    feedback: {
      good:
        reasoning > 0
          ? '사건에서 판단까지 이어지는 연결을 직접 써 줬어요.'
          : '자신의 판단을 분명하게 골랐어요.',
      thinkMore:
        rebuttal > 0
          ? '근거에 자료 속 숫자를 하나 더 붙이면 더 단단해져요.'
          : '반대로 움직일 수 있는 다른 힘이나 위험도 한 가지 적어 보세요.',
      chain,
      chainComment: missing.length
        ? `${missing.join(', ')}까지 이어 보면 인과 뼈대가 완성돼요.`
        : '인과 뼈대의 개념을 모두 이어서 썼어요.',
    },
  }
}
