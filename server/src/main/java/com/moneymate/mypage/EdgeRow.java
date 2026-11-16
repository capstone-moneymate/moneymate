package com.moneymate.mypage;

/**
 * causal_edges 한 줄.
 *
 * @param from     from_concept
 * @param to       to_concept
 * @param forceDir up(올리는 힘) / down(누르는 힘)
 */
public record EdgeRow(String from, String to, String forceDir) {
}
