package com.moneymate.judgement;

import java.util.Map;

/**
 * POST /api/judgement 응답.
 *
 * @param score   100점 환산 점수. 채점 서버 실패로 채점하지 못했으면 null
 * @param correct 60점 이상이면 true (conventions P17). 채점하지 못했으면 null
 * @param rubric  기준별 점수. 채점하지 못했으면 null
 * @param reasons Claude 채점 이유 {reasoning, rebuttal}. 규칙 채점·재사용·실패면 빈 객체
 * @param grader  "claude" / "rule". 채점하지 못했으면 null
 * @param reused  같은 단계·같은 답안의 이전 채점 결과를 다시 쓴 경우 true
 * @param message 채점하지 못했을 때 보여 줄 고정 문구. 채점했으면 null
 * @param feedback AI 분석 피드백 (잘한 점·더 생각할 점·인과 뼈대). 채점하지 못했으면 null (#56)
 */
public record JudgementResponse(
        Integer score,
        Boolean correct,
        Rubric rubric,
        Map<String, String> reasons,
        String grader,
        boolean reused,
        String message,
        JudgementFeedback feedback) {
}
