package com.moneymate.judgement;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.Map;

/** FastAPI 채점 서버 POST /judge 응답 (worker/judge_api.py 의 JudgeResponse). 쓰는 필드만 받는다. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record JudgeApiResponse(
        Rubric rubric,
        int total,
        int score,
        String grader,
        Map<String, String> reasons,
        JudgementFeedback feedback) {
}
