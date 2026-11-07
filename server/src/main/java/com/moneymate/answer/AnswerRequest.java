package com.moneymate.answer;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.UUID;

/**
 * POST /api/answers 요청. answer 는 web 의 AnswerInput(web/src/types/card.ts) 그대로다.
 * stepId 는 web 이 문자열("10")로 보내도 숫자로 읽힌다.
 */
public record AnswerRequest(
        @NotNull UUID userId,
        @NotNull Long stepId,
        @NotNull @Valid Input answer) {

    /**
     * 사용자가 낸 답.
     *
     * @param kind        quiz / chart / causal_order
     * @param optionIndex quiz·chart 에서 고른 보기 번호 (0부터)
     * @param order       causal_order 에서 놓은 개념 id 순서
     */
    public record Input(@NotBlank String kind, Integer optionIndex, List<String> order) {
    }
}
