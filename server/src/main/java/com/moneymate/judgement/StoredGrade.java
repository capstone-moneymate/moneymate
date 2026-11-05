package com.moneymate.judgement;

/** user_answers 에 저장된 이전 채점 결과 (해시 재사용용). */
public record StoredGrade(int score, int evidence, int reasoning, int rebuttal, String gradedBy) {
}
