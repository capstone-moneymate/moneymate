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

    /** before 보다 앞선 날짜의 카드 (최근 날짜부터, 같은 날은 id 순), 최대 limit 건. */
    List<CardRow> findCardsBefore(@Param("before") LocalDate before,
                                  @Param("includePending") boolean includePending,
                                  @Param("limit") int limit);

    /** 카드 한 건. 없거나 보여 줄 상태가 아니면 빈 값. */
    Optional<CardRow> findCard(@Param("cardId") long cardId, @Param("includePending") boolean includePending);

    /** 카드의 단계들 (step_no 순). steps.answer 는 읽지 않는다. */
    List<StepRow> findSteps(@Param("cardId") long cardId);

    /**
     * 그 날짜 카드 중 홈 종목 차트로 쓸 한 장. worker 가 고른 카드(model_info.select.chart = true)가 먼저,
     * 없으면 대표 자료에 KR·US 종목이 있고 prices 에 일봉이 있는 카드 중 id 가 가장 작은 것. 없으면 빈 값.
     */
    Optional<ChartPickRow> findChartPick(@Param("cardDate") LocalDate cardDate,
                                         @Param("includePending") boolean includePending);

    /** 그 종목의 upTo(포함) 이하 일봉을 최근 날짜부터 최대 limit 개. */
    List<CandleRow> findCandles(@Param("ticker") String ticker, @Param("market") String market,
                                @Param("upTo") LocalDate upTo, @Param("limit") int limit);

    /** 그 종목이 대표 자료인 카드 중 card_date 가 before 보다 앞서고 시장 날짜가 from 이상인 것 (시장 날짜 순). */
    List<ChartNoteRow> findChartNotes(@Param("ticker") String ticker, @Param("market") String market,
                                      @Param("from") LocalDate from, @Param("before") LocalDate before,
                                      @Param("includePending") boolean includePending);

    /** cardIds 중 이 사용자가 답을 내는 단계(concept 제외)에 모두 답을 낸 카드 id. */
    List<Long> findCompletedCardIds(@Param("userId") String userId, @Param("cardIds") List<Long> cardIds);
}
