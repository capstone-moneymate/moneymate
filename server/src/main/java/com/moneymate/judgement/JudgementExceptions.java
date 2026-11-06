package com.moneymate.judgement;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/** 판단 채점 API 의 예외와 HTTP 응답 변환. */
@RestControllerAdvice(assignableTypes = JudgementController.class)
public class JudgementExceptions {

    /** 하루 판단 채점 횟수를 다 썼다 → 429. */
    public static class DailyLimitExceeded extends RuntimeException {
        public DailyLimitExceeded(int limit) {
            super("오늘 판단 채점은 " + limit + "번까지 할 수 있어요. 내일 다시 해 주세요.");
        }
    }

    /** 서비스 전체 하루 판단 채점 상한에 닿았다 → 429. */
    public static class GlobalDailyLimitExceeded extends RuntimeException {
        public GlobalDailyLimitExceeded() {
            super("오늘은 채점 요청이 많아 더 받을 수 없어요. 내일 다시 해 주세요.");
        }
    }

    /** 없는 단계이거나 판단해보기 단계가 아니다 → 404. */
    public static class StepNotFound extends RuntimeException {
        public StepNotFound(long stepId) {
            super("판단해보기 단계를 찾을 수 없어요: " + stepId);
        }
    }

    @ExceptionHandler(DailyLimitExceeded.class)
    ResponseEntity<Map<String, String>> dailyLimit(DailyLimitExceeded e) {
        return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS).body(Map.of("message", e.getMessage()));
    }

    @ExceptionHandler(GlobalDailyLimitExceeded.class)
    ResponseEntity<Map<String, String>> globalDailyLimit(GlobalDailyLimitExceeded e) {
        return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS).body(Map.of("message", e.getMessage()));
    }

    @ExceptionHandler(StepNotFound.class)
    ResponseEntity<Map<String, String>> stepNotFound(StepNotFound e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", e.getMessage()));
    }
}
