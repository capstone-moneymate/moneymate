package com.moneymate.judgement;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.UUID;

/**
 * POST /api/judgement 요청.
 *
 * @param userId 첫 실행 때 브라우저가 만든 익명 ID
 * @param stepId 판단해보기 단계(steps.kind = 'judgement') id
 * @param choice 사용자가 고른 선택지. 채점하지 않고 저장만 한다
 * @param answer 주관식 근거 (필수). 이것만 채점한다
 */
public record JudgementRequest(
        @NotNull UUID userId,
        @NotNull Long stepId,
        @Size(max = 200) String choice,
        @NotBlank @Size(max = 2000) String answer) {
}
