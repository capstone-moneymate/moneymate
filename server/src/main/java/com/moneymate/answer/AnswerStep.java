package com.moneymate.answer;

/**
 * 코드 채점에 필요한 단계 재료. 정답(steps.answer)은 서버 안에서만 쓴다.
 *
 * @param stepId      steps.id
 * @param cardId      cards.id
 * @param kind        steps.kind
 * @param answerJson  steps.answer (JSON 문자열, 없으면 null)
 * @param optionCount steps.content.options 개수 (보기가 없으면 0)
 * @param conceptIds  steps.content.concept_ids (P17 user_concepts 기록용)
 */
public record AnswerStep(
        long stepId,
        long cardId,
        String kind,
        String answerJson,
        int optionCount,
        String[] conceptIds) {
}
