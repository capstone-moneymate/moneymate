package com.moneymate.mypage;

/**
 * 이 사용자의 답안 수 (user_answers).
 *
 * @param graded     채점된 답안 수 (is_correct 가 있는 줄: 코드 채점 + 판단 채점)
 * @param correct    그중 맞은 수 (코드 채점은 정답 일치, 판단은 60점 이상, conventions P17)
 * @param judgements 판단해보기(steps.kind = 'judgement') 제출 수
 */
public record AnswerCounts(int graded, int correct, int judgements) {
}
