package com.moneymate.answer;

import java.time.LocalDate;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/** 지난 답안 읽기 (MyBatis). SQL 은 resources/mapper/answer/AnswerHistoryRepository.xml */
@Mapper
public interface AnswerHistoryRepository {

    /** 이 카드에서 단계마다 마지막 답안, 단계 번호 순. date(KST)가 있으면 그날 낸 답안 중에서 고른다. */
    List<PastAnswerRow> findPastAnswers(@Param("userId") String userId,
                                        @Param("cardId") long cardId,
                                        @Param("date") LocalDate date);
}
