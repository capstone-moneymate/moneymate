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

    /** @param stepId steps.id, kind quiz | chart | causal_order | judgement */
    record GhostStep(long stepId, String kind) {
    }
}
