package com.moneymate.mypage;

import java.time.LocalDate;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 탭3 마이페이지 DB 읽기 (MyBatis). SQL 은 resources/mapper/mypage/MypageRepository.xml
 * 읽기만 한다. user_concepts 에 쓰는 것은 learning 패키지의 recordConceptResult (conventions P17).
 */
@Mapper
public interface MypageRepository {

    /** 이 사용자가 배운 개념 (user_concepts.total > 0), id 순. */
    List<ConceptRow> findLearnedConcepts(@Param("userId") String userId);

    /** 한쪽 끝이라도 이 사용자가 배운 개념(total > 0)에 닿은 사전 연결, causal_edges.id 순. */
    List<EdgeRow> findEdgesTouchingLearned(@Param("userId") String userId);

    /** 개념 id 목록의 이름·테마. 학습 기록은 읽지 않아 correct·total 은 0, id 순. */
    List<ConceptRow> findConcepts(@Param("ids") List<String> ids);

    /** 답안을 낸 날 (KST 날짜, 중복 없이 최근 순). 연속 학습 계산용. */
    List<LocalDate> findAnswerDays(@Param("userId") String userId);

    /** 채점된 답안 수·맞은 수·판단해보기 제출 수. 기록이 없으면 0, 0, 0. */
    AnswerCounts countAnswers(@Param("userId") String userId);
}
