package com.moneymate.news;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/** 탭1 뉴스 홈·카드 DB 읽기 (MyBatis). SQL 은 resources/mapper/news/NewsRepository.xml */
@Mapper
public interface NewsRepository {

    /** 지수마다 가장 최근 거래일 종가와 그 전 거래일 종가. prices 에 없는 지수는 빠진다. */
    List<IndexRow> findLatestIndices(@Param("tickers") List<String> tickers);

    /** today(KST) 이하에서 보여 줄 카드가 있는 가장 최근 card_date. 없으면 빈 값. */
    Optional<LocalDate> findLatestCardDate(@Param("today") LocalDate today,
                                           @Param("includePending") boolean includePending);

    /** 그 날짜의 카드 목록 (id 순). */
    List<CardRow> findCardsByDate(@Param("cardDate") LocalDate cardDate,
                                  @Param("includePending") boolean includePending);

    /** 카드 한 건. 없거나 보여 줄 상태가 아니면 빈 값. */
    Optional<CardRow> findCard(@Param("cardId") long cardId, @Param("includePending") boolean includePending);

    /** 카드의 단계들 (step_no 순). steps.answer 는 읽지 않는다. */
    List<StepRow> findSteps(@Param("cardId") long cardId);

    /** cardIds 중 이 사용자가 답을 내는 단계(concept 제외)에 모두 답을 낸 카드 id. */
    List<Long> findCompletedCardIds(@Param("userId") String userId, @Param("cardIds") List<Long> cardIds);
}
