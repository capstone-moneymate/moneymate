package com.moneymate.answer;

import java.time.LocalDate;

/**
 * 고스트 비교용 답안 한 줄 (user_answers). 한 시도에서 같은 단계를 여러 번 냈으면 마지막 답안.
 *
 * @param attemptNo  user_answers.attempt_no (몇 번째 시도, #215)
 * @param stepId     steps.id
 * @param isCorrect  맞았는가 (판단은 60점 이상, 채점 못 했으면 null)
 * @param score      판단 100점 환산 (코드 채점 단계는 null)
 * @param confidence 1 헷갈려요, 2 확실해요 (판단, 확신 버튼 이전 답안은 null)
 * @param responseMs 문제가 뜬 순간 ~ 낼 때까지 (없으면 null)
 * @param day        그 시도를 시작한 날 (KST, 그 시도의 첫 답안 날짜)
 */
public record GhostRow(int attemptNo, long stepId, Boolean isCorrect, Integer score, Integer confidence,
                       Integer responseMs, LocalDate day) {
}
