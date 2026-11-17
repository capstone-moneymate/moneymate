package com.moneymate.judgement;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonRawValue;

/**
 * FastAPI 채점 서버 POST /judge 요청 (worker/judge_api.py 의 JudgeRequest).
 * keyFacts·chain·counter·debate 는 DB 가 만든 JSON 문자열을 그대로 끼워 넣는다 (@JsonRawValue).
 * debate 가 null 이면 JSON null 로 가고, 채점 서버는 토론 없이 채점한다.
 */
public record JudgeApiRequest(
        String answer,
        @JsonProperty("key_facts") @JsonRawValue String keyFacts,
        @JsonRawValue String chain,
        @JsonRawValue String counter,
        @JsonProperty("card_id") Long cardId,
        @JsonProperty("step_id") Long stepId,
        @JsonRawValue String debate) {
}
