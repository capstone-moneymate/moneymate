package com.moneymate.overlap;

import java.time.LocalDate;

/**
 * stock_reasons 한 줄 (004, conventions P19). C 의 reasons.save() 가 쓰고 서버는 published 만 읽는다.
 *
 * @param bigPeriodEnd 13F 분기 말
 * @param direction    종목 단위 방향 same / diff / none (규칙은 docs/modules/reasons.md)
 * @param change       큰손 쪽 변화 up / down
 * @param headline     카드 ② 제목
 * @param reasonsJson  카드 ② 이유 JSON 배열 (snake_case, reasons.md "저장 모양")
 * @param nowViewJson  카드 ③ 지금은 JSON (stock_now.to_json()), 없으면 null
 */
public record StockReasonsRow(
        LocalDate bigPeriodEnd,
        String direction,
        String change,
        String headline,
        String reasonsJson,
        String nowViewJson) {
}
