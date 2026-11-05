package com.moneymate.judgement;

import java.time.OffsetDateTime;
import java.util.Optional;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/** 판단 채점 DB 접근 (MyBatis). SQL 은 resources/mapper/judgement/JudgementRepository.xml */
@Mapper
public interface JudgementRepository {

    /** 판단해보기 단계의 채점 재료. 없거나 kind 가 judgement 가 아니면 빈 값. */
    Optional<JudgementStep> findStep(@Param("stepId") long stepId);

    /** 사용자가 since 이후 낸 판단 답안 수 (하루 호출 제한). */
    int countJudgementsSince(@Param("userId") String userId, @Param("since") OffsetDateTime since);

    /** 같은 단계·같은 답안 해시로 Claude 가 채점한 가장 최근 결과. */
    Optional<StoredGrade> findReusable(@Param("stepId") long stepId, @Param("answerHash") String answerHash);

    /** users 에 없으면 넣는다 (user_answers 의 외래키). */
    void ensureUser(@Param("userId") String userId);

    /** 답안 1개 저장. 채점하지 못했으면 score·rubric·gradedBy·isCorrect 가 null. */
    void insertAnswer(@Param("userId") String userId,
                      @Param("cardId") long cardId,
                      @Param("stepId") long stepId,
                      @Param("choice") String choice,
                      @Param("answer") String answer,
                      @Param("answerHash") String answerHash,
                      @Param("isCorrect") Boolean isCorrect,
                      @Param("score") Integer score,
                      @Param("rubric") Rubric rubric,
                      @Param("gradedBy") String gradedBy);
}
