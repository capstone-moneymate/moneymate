package com.moneymate.news;

import java.time.LocalDate;

/**
 * 차트 종목이 대표 자료였던 지난 카드 한 장 → 차트 위 ○ 와 말풍선.
 *
 * @param cardId     cards.id
 * @param marketDate raw_sources.published_date (그 시장 날짜, 이 날짜의 일봉 위에 ○)
 * @param title      cards.title
 * @param slidesJson cards.slides (첫 슬라이드 본문을 말풍선 문장으로 쓴다)
 */
public record ChartNoteRow(long cardId, LocalDate marketDate, String title, String slidesJson) {
}
