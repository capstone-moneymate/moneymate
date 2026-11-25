package com.moneymate.answer;

import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/** 고스트 비교용 읽기 (MyBatis). SQL 은 resources/mapper/answer/GhostRepository.xml */
@Mapper
public interface GhostRepository {

    /** 이 카드의 답 단계(개념 단계 제외), 단계 번호 순 */
    List<GhostStep> findSteps(@Param("cardId") long cardId);

    /** 이 카드에서 낸 답안을 (시도, 단계)마다 마지막 것 하나씩. 시도 번호 순 */
    List<GhostRow> findRows(@Param("userId") String userId, @Param("cardId") long cardId);

    /** 이 카드의 개념 단계에서 튜터가 낸 퀴즈를 시도마다 센 것 (concept_answers, source = tutor). 시도 번호 순 */
    List<GhostConcept> findConceptRows(@Param("userId") String userId, @Param("cardId") long cardId);

    /** @param stepId steps.id, kind quiz | chart | causal_order | judgement */
    record GhostStep(long stepId, String kind) {
    }

    /**
     * 한 시도의 개념 단계 기록.
     *
     * @param attemptNo concept_answers.attempt_no (본 문제의 시도 번호와 같다, #230)
     * @param quizzes   튜터가 낸 퀴즈 수
     * @param correct   그중 맞힌 수
     */
    record GhostConcept(int attemptNo, int quizzes, int correct) {
    }
}
