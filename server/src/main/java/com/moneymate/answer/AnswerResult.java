package com.moneymate.answer;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * POST /api/answers 응답. web 의 AnswerResult(web/src/types/card.ts) 모양.
 *
 * @param stepId      steps.id (문자열)
 * @param isCorrect   코드 채점 결과
 * @param explanation 해설 (steps.answer.explanation)
 * @param correct     정답: quiz·chart 는 보기 번호(Integer), causal_order 는 개념 id 순서(List)
 */
public record AnswerResult(
        String stepId,
        @JsonProperty("isCorrect") boolean isCorrect,
        String explanation,
        Object correct) {
}
