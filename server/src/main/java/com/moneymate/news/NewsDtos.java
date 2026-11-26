package com.moneymate.news;

import java.util.List;
import java.util.Map;

/**
 * 탭1 뉴스·카드 API 응답. 모양은 web/src/types/news.ts, web/src/types/card.ts 와 같다.
 * id 는 web 타입에 맞춰 문자열로 내려보낸다.
 */
public final class NewsDtos {

    private NewsDtos() {
    }

    /** 주요 지수 한 칸. chgPct 는 소수(0.012 = +1.2%), date 는 그 시장 거래일(YYYY-MM-DD). */
    public record MarketIndex(String code, String name, double value, Double chgPct, String date) {
    }

    /** 홈에 보이는 카드 한 건. */
    public record NewsCardSummary(
            String id,
            int type,
            String title,
            String summary,
            String theme,
            String sourceName,
            String sourceUrl,
            String sourcePublishedAt,
            int stepCount) {
    }

    /** 지난 뉴스 한 건: 홈 카드와 같은 내용 + 그 카드의 날짜(cards.card_date, YYYY-MM-DD). */
    public record PastCard(String date, NewsCardSummary card) {
    }

    /** GET /api/news/past. 최근 날짜부터. completedCardIds 는 그중 이 사용자가 학습을 끝낸 카드. */
    public record PastNews(List<PastCard> cards, List<String> completedCardIds) {
    }

    /** GET /api/news/home. stockChart 는 그날 차트를 그릴 종목 카드가 없으면 null. */
    public record NewsHome(
            String date,
            StockChart stockChart,
            List<MarketIndex> indices,
            List<NewsCardSummary> cards,
            List<String> completedCardIds) {
    }

    /** 일봉 하나 (date = 그 시장 거래일). */
    public record Candle(String date, double open, double high, double low, double close) {
    }

    /** 차트 날짜 하나에 붙는 설명. pastCardId 가 있으면 화면이 그날 위에 ○ 를 띄운다. */
    public record StockChartNote(String date, String reason, String pastCardId, String pastCardTitle) {
    }

    /**
     * 탭1 홈 종목 차트 (web/src/types/news.ts StockChart).
     * today = 홈 카드 날짜, candles = today 앞까지 최근 거래일(5일선용으로 앞 4일 더),
     * todayClose = today 일봉이 이미 있으면 그 종가(O/X 퀴즈 정답), 없으면 null.
     */
    public record StockChart(
            String ticker,
            String name,
            String market,
            String today,
            String todayCardId,
            Double todayClose,
            List<Candle> candles,
            List<StockChartNote> notes) {
    }

    /**
     * GET /api/cards/{id}. slides·steps 는 DB JSON 의 키를 camelCase 로 바꾼 것.
     * steps 의 각 항목은 {id, no, kind, conceptIds, ...kind 별 content} 이고 정답은 없다.
     */
    public record CardDetail(
            String id,
            int type,
            String title,
            String theme,
            String sourceName,
            String sourceUrl,
            String sourcePublishedAt,
            String ticker,
            List<Map<String, Object>> slides,
            List<Map<String, Object>> steps) {
    }
}
