package com.moneymate.tutor;

import com.fasterxml.jackson.annotation.JsonAlias;
import java.util.List;
import java.util.Map;

/**
 * 튜터 응답 (사람1, #240). 채점 서버(worker/tutor/api.py)가 준 값을 그대로 화면에 넘긴다.
 * 채점 서버는 snake_case(session_id)로 주고 화면에는 camelCase(sessionId)로 나간다 (@JsonAlias 로 읽기만 맞춘다, LearnerDtos 와 같다).
 */
public final class TutorDtos {

    private TutorDtos() {
    }

    /**
     * @param sessionId  튜터 세션 id. 답을 낼 때 쓴다
     * @param status     waiting(퀴즈 답 기다림) / done / error
     * @param finishedBy 끝난 이유. go_main(본 문제로), quiz_limit, call_limit, no_tool, no_targets(개념 단계 용어가 없는 카드), stop:오류
     * @param targets    이 카드의 목표 개념
     * @param quizzes    지금까지 낸 퀴즈 수
     * @param maxQuizzes 퀴즈 상한
     * @param events     이번 요청에서 새로 생긴 이벤트 (조회는 전부). 순서대로 그린다.
     *                   type 이 explain {concept, style, text}, quiz {kind, concept, content, guess_p} (정답 없음),
     *                   graded {concept, kind, correct, key, explanation} (답한 뒤라 정답 포함), done {by}.
     *                   이벤트 안의 키는 채점 서버 그대로(snake_case)다
     */
    public record TutorState(
            @JsonAlias("session_id") String sessionId,
            String status,
            @JsonAlias("finished_by") String finishedBy,
            List<String> targets,
            int quizzes,
            @JsonAlias("max_quizzes") int maxQuizzes,
            List<Map<String, Object>> events) {
    }
}
