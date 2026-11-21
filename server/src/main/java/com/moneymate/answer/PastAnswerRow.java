package com.moneymate.answer;

/**
 * 지난 답안 한 줄 (user_answers + steps). 같은 단계를 여러 번 냈으면 고른 날의 마지막 답안.
 *
 * @param stepId       steps.id
 * @param kind         steps.kind
 * @param answerJson   user_answers.answer (코드 채점: {kind, option_index | order}, 판단: {choice, text})
 * @param isCorrect    user_answers.is_correct (판단은 60점 이상, 채점 못 했으면 null)
 * @param score        user_answers.score (판단 100점 환산, 없으면 null)
 * @param rubricJson   user_answers.rubric ({evidence, reasoning, rebuttal}, 없으면 null)
 * @param feedbackJson user_answers.feedback ({feedback, reasons}, 없으면 null)
 * @param gradedBy     user_answers.graded_by (code | rule | llm)
 * @param keyJson      steps.answer (정답·해설, 판단이면 null 일 수 있다)
 */
public record PastAnswerRow(long stepId, String kind, String answerJson, Boolean isCorrect, Integer score,
                            String rubricJson, String feedbackJson, String gradedBy, String keyJson) {
}
