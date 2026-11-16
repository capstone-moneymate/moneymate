package com.moneymate.overlap;

import java.util.List;

/**
 * 탭2 겹침 API 응답. 변화율은 소수(0.05 = +5%), 날짜는 YYYY-MM-DD 문자열.
 * 방향(direction)과 변화 종류(changeType)는 DB 의 영어 상수 그대로이고 한글 변환은 화면이 한다.
 */
public final class OverlapDtos {

    private OverlapDtos() {
    }

    /** 큰손 한 명의 13F 변화 (holdings_13f 값 그대로). */
    public record FilerChange(
            String filerKey,
            String filerName,
            String changeType,
            Double chgPct,
            String periodEnd,
            String filedAt) {
    }

    /** 액티브 ETF 하나의 추세·어제 변화. trendChgPct 는 overlap_results, dayChgPct 는 holdings_etf 값 그대로. */
    public record EtfChange(
            String etfCode,
            String snapshotDate,
            Double trendChgPct,
            Double dayChgPct) {
    }

    /** (큰손, ETF) 한 쌍의 방향 비교 결과. same / diff / none. */
    public record DirectionPair(String filerKey, String etfCode, String direction) {
    }

    /** 종목 하나의 겹침. 목록의 한 항목이자 종목 상세 응답. */
    public record StockOverlap(
            String calcDate,
            String ticker,
            String issuerName,
            String etfStockName,
            List<FilerChange> filers,
            List<EtfChange> etfs,
            List<DirectionPair> pairs) {
    }

    /** GET /api/overlaps. 겹침 결과가 하나도 없으면 calcDate 는 null, stocks 는 빈 목록. */
    public record OverlapList(String calcDate, List<StockOverlap> stocks) {
    }
}
