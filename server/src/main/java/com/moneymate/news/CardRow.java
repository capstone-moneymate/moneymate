package com.moneymate.news;

import java.time.LocalDate;
import java.time.OffsetDateTime;

/**
 * cards 한 줄 + 대표 1차 자료(card_sources.is_main → raw_sources) + 시작 개념 테마 + 단계 수.
 *
 * @param id                  cards.id
 * @param cardType            cards.card_type (1/2/3)
 * @param cardDate            cards.card_date
 * @param title               cards.title
 * @param theme               cards.start_concept 의 concepts.theme (시작 개념이 없으면 null)
 * @param ticker              cards.ticker (유형 3만)
 * @param slidesJson          cards.slides (JSON 배열 문자열)
 * @param sourceType          raw_sources.source_type (dart / sec_8k / macro). 대표 자료가 없으면 null
 * @param issuerName          raw_sources.issuer_name, 없으면 cards.source_links[0].name
 * @param sourceUrl           raw_sources.url, 없으면 cards.source_links[0].url
 * @param sourcePublishedAt   raw_sources.published_at (DART 는 시각을 몰라 null)
 * @param sourcePublishedDate raw_sources.published_date (그 시장 날짜)
 * @param stepCount           steps 개수
 */
public record CardRow(
        long id,
        int cardType,
        LocalDate cardDate,
        String title,
        String theme,
        String ticker,
        String slidesJson,
        String sourceType,
        String issuerName,
        String sourceUrl,
        OffsetDateTime sourcePublishedAt,
        LocalDate sourcePublishedDate,
        int stepCount) {
}
