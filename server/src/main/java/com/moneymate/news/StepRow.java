package com.moneymate.news;

/**
 * steps 한 줄. 정답(steps.answer)은 일부러 담지 않는다.
 *
 * @param id          steps.id
 * @param stepNo      steps.step_no
 * @param kind        concept / quiz / causal_order / chart / judgement
 * @param contentJson steps.content (사용자에게 보이는 부분, snake_case JSON 문자열)
 */
public record StepRow(long id, int stepNo, String kind, String contentJson) {
}
