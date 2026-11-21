package com.moneymate.mypage;

import java.time.LocalDate;

/**
 * 학습 달력의 한 줄: 어느 날(KST) 어느 카드에서 문제를 몇 개 풀었나.
 * 같은 날 같은 단계를 여러 번 냈으면 그날 마지막 답안만 센다.
 *
 * @param day       답안을 낸 날 (KST)
 * @param cardId    cards.id
 * @param title     cards.title
 * @param cardDate  cards.card_date (카드가 노출된 날. 지난 뉴스를 풀었으면 day 와 다르다)
 * @param stepCount 이 카드의 문제 수 (concept 단계 제외)
 * @param answered  그날 답한 문제 수
 * @param graded    그중 채점된 수 (is_correct 가 있는 답안)
 * @param correct   그중 맞은 수
 */
public record CalendarRow(LocalDate day, String cardId, String title, LocalDate cardDate,
                          int stepCount, int answered, int graded, int correct) {
}
