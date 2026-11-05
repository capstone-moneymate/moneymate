package com.moneymate.judgement;

/**
 * 채점에 필요한 판단 단계 재료. DB 에서 JSON 문자열로 바로 만들어 온다.
 *
 * @param stepId      steps.id
 * @param cardId      cards.id
 * @param keyFactsJson cards.key_facts (없으면 "[]")
 * @param chainJson   steps.answer.chain 개념 id 를 순서대로 concepts 의 [{"name","aliases"}] 로 바꾼 것
 * @param counterJson steps.answer.counter 를 같은 형식으로 바꾼 것
 * @param conceptIds  chain 개념 id (나중에 user_concepts 기록용, P17)
 */
public record JudgementStep(
        long stepId,
        long cardId,
        String keyFactsJson,
        String chainJson,
        String counterJson,
        String[] conceptIds) {
}
