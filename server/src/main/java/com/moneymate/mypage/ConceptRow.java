package com.moneymate.mypage;

/**
 * 개념 한 줄 + 이 사용자의 학습 기록.
 *
 * @param id      concepts.id
 * @param name    concepts.name
 * @param theme   concepts.theme
 * @param correct user_concepts.correct (기록이 없는 이웃 개념이면 0)
 * @param total   user_concepts.total (기록이 없는 이웃 개념이면 0)
 */
public record ConceptRow(String id, String name, String theme, int correct, int total) {
}
