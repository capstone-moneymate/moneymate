package com.moneymate.answer;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import java.util.List;
import java.util.UUID;

/**
 * POST /api/answers 요청. answer 는 web 의 AnswerInput(web/src/types/card.ts) 그대로다.
 * stepId 는 web 이 문자열("10")로 보내도 숫자로 읽힌다.
 *
 * 아래 셋은 학습자 상태용이다 (docs/추가구현_계획.md 2-1, 2-2). 채점에는 쓰지 않고 저장만 한다. 안 보내면 null.
 *
 * @param confidence    정답을 보기 전에 누른 확신: 1 애매해요, 2 확신해요
 * @param responseMs    문제가 화면에 뜬 순간부터 낼 때까지 (ms, 화면이 잰다)
 * @param answerChanges 내기 전에 답을 바꾼 횟수
 */
public record AnswerRequest(
        @NotNull UUID userId,
        @NotNull Long stepId,
        @NotNull @Valid Input answer,
        @Min(1) @Max(2) Integer confidence,
        @PositiveOrZero Integer responseMs,
        @PositiveOrZero Integer answerChanges) {

    /** 확신·시간 없이 답만 (이전 화면, 테스트). */
    public AnswerRequest(UUID userId, Long stepId, Input answer) {
        this(userId, stepId, answer, null, null, null);
    }

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
