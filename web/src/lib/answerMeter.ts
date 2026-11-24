import { useEffect, useRef } from 'react'
import type { AnswerMeta, Confidence } from '@/types/card'

/**
 * 문제 하나를 푸는 동안의 응답 시간과 답을 바꾼 횟수를 잰다 (사용자 입력 없음, 답과 함께 서버에 저장).
 * - 응답 시간: 문제가 화면에 뜬 순간(이 훅을 쓴 화면이 처음 그려진 때) ~ read() 를 부른 순간 (ms)
 * - 답 변경: 화면이 changed() 를 부른 횟수. 처음 고르는 것은 세지 않고, 고른 답을 다른 것으로 바꿀 때만 센다
 * 단계 화면은 LearnPage 가 key={step.id} 로 새로 그리므로 문제마다 0부터 다시 잰다.
 */
export const useAnswerMeter = () => {
  const startedAt = useRef<number | null>(null)
  const changes = useRef(0)

  useEffect(() => {
    startedAt.current = performance.now()
    changes.current = 0
  }, [])

  return {
    changed: () => {
      changes.current += 1
    },
    read: (confidence: Confidence): AnswerMeta => ({
      confidence,
      responseMs:
        startedAt.current === null ? 0 : Math.round(performance.now() - startedAt.current),
      answerChanges: changes.current,
    }),
  }
}
