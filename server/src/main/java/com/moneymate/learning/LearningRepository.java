package com.moneymate.learning;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/** 개념 학습 기록(user_concepts) DB 접근 (MyBatis). SQL 은 resources/mapper/learning/LearningRepository.xml */
@Mapper
public interface LearningRepository {

    /** users 에 없으면 넣는다 (user_concepts 의 외래키). */
    void ensureUser(@Param("userId") String userId);

    /**
     * 개념마다 total +1, correct 면 correct +1 (없으면 새 줄). concepts 에 없는 id 는 건너뛴다.
     *
     * @return 실제로 기록한 개념 수
     */
    int upsertConceptResults(@Param("userId") String userId,
                             @Param("conceptIds") String[] conceptIds,
                             @Param("correct") boolean correct);
}
