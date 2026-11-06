package com.moneymate.judgement;

/** 루브릭 기준별 점수 (증거 0~2, 추론 0~4, 반박 0~3). 범위 자르기·합계는 Python 채점 함수가 한다. */
public record Rubric(int evidence, int reasoning, int rebuttal) {
}
