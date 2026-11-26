package com.moneymate.news;

/**
 * 홈 종목 차트로 쓸 카드 한 장과 그 종목 (대표 자료 card_sources.is_main → raw_sources).
 *
 * @param cardId cards.id (차트 오늘 칸을 누르면 가는 카드)
 * @param ticker raw_sources.ticker (국내 6자리 / 미국 티커, conventions 그대로)
 * @param market raw_sources.market (KR / US)
 * @param name   raw_sources.issuer_name (없으면 ticker)
 */
public record ChartPickRow(long cardId, String ticker, String market, String name) {
}
