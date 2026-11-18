package com.moneymate.overlap;

import com.fasterxml.jackson.annotation.JsonUnwrapped;
import java.util.List;
import java.util.Map;

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

    /** 카드 ② 인과 경로의 개념 하나. learned 는 이 사용자가 배운 개념인지 (userId 가 없으면 false). */
    public record PathConcept(String id, String name, boolean learned) {
    }

    /** 카드 ② 근거 자료. no 는 C 가 붙인 번호 그대로이고 화면이 1부터 다시 매긴다. 기사 본문은 없다(제목·링크만). */
    public record ReasonEvidence(Integer no, String publishedDate, String title, String issuerName, String url) {
    }

    /**
     * 카드 ② 이유 하나. direction 은 경로 시작 개념이 커질 때 끝 개념이 받는 힘(up/down).
     * inMyMap 은 경로에 사용자가 배운 개념이 하나라도 있는지 ("내 지도에 있어요").
     */
    public record StockReason(
            String title,
            String body,
            List<PathConcept> path,
            String direction,
            boolean inMyMap,
            List<ReasonEvidence> evidence) {
    }

    /** 카드 ③ 기준일 이후 주가. returnPct 는 퍼센트 값 (12.5 = 12.5%, C 가 저장한 그대로). */
    public record NowPrice(String fromDate, Double fromClose, String toDate, Double toClose, Double returnPct) {
    }

    /** 카드 ③ 기준일 뒤 자료. numbers 는 공시에서 코드가 뽑은 값 (키는 한글 이름). */
    public record NowSource(String publishedDate, String title, String url, Map<String, Object> numbers) {
    }

    /** 카드 ③ 이유 경로 개념 중 오늘 탭 1 카드가 다룬 개념. */
    public record NowLinked(String conceptId, String name, String reasonTitle) {
    }

    /** 카드 ③ 지금은. price 는 종가가 없으면 null, text 는 문장 검사를 못 넘으면 null (사실만 보여 준다). */
    public record StockNow(String baseDate, NowPrice price, List<NowSource> laterSources, List<NowLinked> linked,
                           String text) {
    }

    /** 카드 ②③ (stock_reasons 의 published 최근 분기 한 줄, P19). now 는 카드 ③이 아직 없으면 null. */
    public record StockReasons(
            String bigPeriodEnd,
            String direction,
            String change,
            String headline,
            List<StockReason> reasons,
            StockNow now) {
    }

    /**
     * GET /api/stocks/{ticker}. 겹침 필드(StockOverlap)는 목록 항목과 같은 자리에 펼치고 카드 ②③과
     * "내 지도에 있어요"를 더한다. reasons 는 published 이유가 없으면 null,
     * reasonsRejected 는 reasons 가 null 이고 가장 최근 분기 이유가 검사에서 전부 버려졌을 때(rejected) true (#164),
     * myConcepts 는 이 종목에 연결된 개념(#100) 중 사용자가 배운 것 (userId 가 없으면 빈 목록).
     */
    public record StockDetail(
            @JsonUnwrapped StockOverlap overlap,
            StockReasons reasons,
            boolean reasonsRejected,
            List<MyMapConcept> myConcepts) {
    }

    /** "내 지도에 있어요" 개념 하나 (사용자가 배운 개념). id 는 concepts.id 그대로. */
    public record MyMapConcept(String id, String name, String theme) {
    }

    /** 사용자가 배운 개념과 연결된 종목 하나와 그 개념들. */
    public record MyMapTicker(String ticker, List<MyMapConcept> concepts) {
    }

    /** GET /api/overlaps. 겹침 결과가 하나도 없으면 calcDate 는 null, stocks 는 빈 목록. */
    public record OverlapList(String calcDate, List<StockOverlap> stocks) {
    }
}
