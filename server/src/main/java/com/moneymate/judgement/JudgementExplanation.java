package com.moneymate.judgement;

/**
 * 판단해보기 "모르겠어요, 설명 볼래요" 응답. 카드의 낙관·비관 토론(card_debates, published 만, P21).
 * 토론이 아직 없으면 bull·bear 가 null 이고 화면은 준비 중 문구를 보여 준다.
 */
public record JudgementExplanation(String bull, String bear) {

    static final JudgementExplanation EMPTY = new JudgementExplanation(null, null);
}
