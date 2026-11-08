package com.moneymate.answer;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/** 코드 채점 답안 API 의 예외와 HTTP 응답 변환. */
@RestControllerAdvice(assignableTypes = AnswerController.class)
public class AnswerExceptions {

    /** 없는 단계이거나 보여 줄 상태가 아닌 카드의 단계 → 404. */
    public static class StepNotFound extends RuntimeException {
        public StepNotFound(long stepId) {
            super("단계를 찾을 수 없어요: " + stepId);
        }
    }

    /** 단계와 맞지 않는 답 (kind 다름, 보기 번호 범위 밖, 순서 개념 다름, 판단해보기) → 400. */
    public static class BadAnswer extends RuntimeException {
        public BadAnswer(String message) {
            super(message);
        }
    }

    /** DB 에 저장된 정답이 없거나 형식이 다르다 (출제 쪽 문제) → 500. */
    public static class AnswerKeyMissing extends RuntimeException {
        public AnswerKeyMissing(long stepId) {
            super("이 단계의 정답을 읽지 못했어요: " + stepId);
        }
    }

    @ExceptionHandler(StepNotFound.class)
    ResponseEntity<Map<String, String>> stepNotFound(StepNotFound e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", e.getMessage()));
    }

    @ExceptionHandler(BadAnswer.class)
    ResponseEntity<Map<String, String>> badAnswer(BadAnswer e) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("message", e.getMessage()));
    }

    @ExceptionHandler(AnswerKeyMissing.class)
    ResponseEntity<Map<String, String>> keyMissing(AnswerKeyMissing e) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("message", e.getMessage()));
    }
}
