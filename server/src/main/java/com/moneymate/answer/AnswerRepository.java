package com.moneymate.answer;

import java.util.Optional;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/** 코드 채점 답안 DB 접근 (MyBatis). SQL 은 resources/mapper/answer/AnswerRepository.xml */
@Mapper
public interface AnswerRepository {

    /** 단계와 정답. 없거나 카드가 보여 줄 상태(published, 설정 시 pending)가 아니면 빈 값. */
    Optional<AnswerStep> findStep(@Param("stepId") long stepId, @Param("includePending") boolean includePending);

    /** users 에 없으면 넣는다 (user_answers 의 외래키). */
    void ensureUser(@Param("userId") String userId);

    /** 코드 채점 답안 1개 저장 (graded_by = 'code'). answerJson 은 사용자가 낸 답 JSON 문자열. */
    void insertAnswer(@Param("userId") String userId,
                      @Param("cardId") long cardId,
                      @Param("stepId") long stepId,
                      @Param("answerJson") String answerJson,
                      @Param("isCorrect") boolean isCorrect);
}
