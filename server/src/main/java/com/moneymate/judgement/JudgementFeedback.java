package com.moneymate.judgement;

import com.fasterxml.jackson.annotation.JsonAlias;
import java.util.List;

/**
 * AI 분석 피드백 (#56). 판단해보기 결과 화면의 잘한 점·더 생각할 점·인과 뼈대.
 * FastAPI 는 snake_case(think_more, chain_comment)로 보내고, 웹에는 camelCase 로 내려간다 (@JsonAlias 는 읽을 때만).
 *
 * @param good         잘한 점
 * @param thinkMore    더 생각할 점
 * @param chain        인과 뼈대: 카드의 chain 개념 순서와 사용자가 썼는지 (Python 코드가 정함)
 * @param chainComment 인과 뼈대 설명 한 문장
 */
public record JudgementFeedback(
        String good,
        @JsonAlias("think_more") String thinkMore,
        List<ChainItem> chain,
        @JsonAlias("chain_comment") String chainComment) {

    /** 인과 뼈대 개념 1개. used = 사용자 답안에 이 개념이 있었는지. */
    public record ChainItem(String name, boolean used) {
    }
}
