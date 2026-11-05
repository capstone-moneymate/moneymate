package com.moneymate.judgement;

/**
 * user_answers 에 저장된 이전 채점 결과 (해시 재사용용).
 *
 * @param feedbackJson user_answers.feedback. {"feedback": {...}, "reasons": {...}} JSON 문자열 (#56). 예전 줄은 null
 */
public record StoredGrade(int score, int evidence, int reasoning, int rebuttal, String gradedBy, String feedbackJson) {
}
