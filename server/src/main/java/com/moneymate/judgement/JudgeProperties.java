package com.moneymate.judgement;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** application.yml 의 moneymate.judge.* 설정. */
@ConfigurationProperties("moneymate.judge")
public record JudgeProperties(String url, int timeoutSeconds, int dailyLimit) {
}
