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

    /** GET /api/news/home */
    public record NewsHome(
            String date,
            List<MarketIndex> indices,
            List<NewsCardSummary> cards,
            List<String> completedCardIds) {
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
