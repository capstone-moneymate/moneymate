package com.moneymate.answer;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * GET /api/answers/history 의 단계 하나. 화면이 그 단계를 "풀었던 상태"로 다시 그릴 재료.
 *
 * @param stepId 단계 id (문자열)
 * @param input  내가 낸 답. quiz·chart {kind, optionIndex}, causal_order {kind, order}, judgement {kind, choice, reason}
 * @param result 채점 결과 = web 의 AnswerResult 모양 (POST /api/answers·/api/judgement 응답과 같은 이름)
 */
public record PastAnswer(String stepId, Map<String, Object> input, Result result) {

    /**
     * @param isCorrect   맞았는가 (판단은 60점 이상, 채점 못 했으면 null)
     * @param explanation 해설 (코드 채점 단계)
     * @param correct     정답: 보기 번호 또는 개념 id 순서 (코드 채점 단계)
     * @param grade       판단 채점 결과 (JudgementGrade 모양, 판단 단계만)
     */
    public record Result(String stepId, @JsonProperty("isCorrect") Boolean isCorrect, String explanation,
                         Object correct, Map<String, Object> grade) {
    }
}
