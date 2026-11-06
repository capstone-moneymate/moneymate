package com.moneymate.judgement;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * application.yml 의 moneymate.judge.* 설정.
 *
 * @param dailyLimit       사용자별 하루 판단 채점 횟수 상한
 * @param globalDailyLimit 서비스 전체 하루 판단 채점 횟수 상한 (userId 를 바꿔 피하는 것을 막는다)
 */
@ConfigurationProperties("moneymate.judge")
public record JudgeProperties(String url, int timeoutSeconds, int dailyLimit, int globalDailyLimit) {
}
