package com.moneymate.overlap;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/** 탭2 겹침 DB 읽기 (MyBatis). SQL 은 resources/mapper/overlap/OverlapRepository.xml */
@Mapper
public interface OverlapRepository {

    /** overlap_results 의 가장 최근 calc_date. 결과가 없으면 빈 값. */
    Optional<LocalDate> findLatestCalcDate();

    /** 그 계산일의 겹침 행 (ticker, filer_key, etf_code 순). ticker 가 null 이면 전체. */
    List<OverlapRow> findRows(@Param("calcDate") LocalDate calcDate, @Param("ticker") String ticker);
}
