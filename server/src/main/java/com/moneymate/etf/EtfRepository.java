package com.moneymate.etf;

import java.util.List;
import org.apache.ibatis.annotations.Mapper;

/** 탭2 액티브 ETF DB 읽기 (MyBatis). SQL 은 resources/mapper/etf/EtfRepository.xml */
@Mapper
public interface EtfRepository {

    /** ETF 마다 가장 최근 스냅샷 날짜 (etf_code 순). */
    List<EtfRow> findLatestSnapshots();

    /** ETF 마다 가장 최근 스냅샷에서 어제 변화(day_chg_pct)가 있는 구성종목 (etf_code, raw_code 순). */
    List<EtfRow> findLatestMoves();
}
