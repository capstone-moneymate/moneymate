package com.moneymate.overlap;

/**
 * "내 지도에 있어요" 한 줄: 사용자가 배운 개념(user_concepts.total > 0)과 그 개념에 연결된 종목 (concept_tickers, 005).
 *
 * @param ticker      concept_tickers.ticker
 * @param conceptId   concepts.id (B 의 사전 id 그대로. user_concepts.concept_id 와 같은 값)
 * @param conceptName concepts.name
 * @param theme       concepts.theme
 */
public record MyMapRow(String ticker, String conceptId, String conceptName, String theme) {
}
