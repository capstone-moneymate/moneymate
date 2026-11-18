package com.moneymate.auth;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * 회원가입·로그인 예외와 HTTP 응답 변환.
 * LoginRequired 는 다른 API(answers·judgement·mypage·news·stocks)의 UserGuard 에서도 나서 전체에 건다.
 * 여기 적은 예외 종류만 다루므로 다른 컨트롤러의 예외 처리와 겹치지 않는다.
 */
@RestControllerAdvice
public class AuthExceptions {

    /** 계정에 붙은 userId 인데 그 계정으로 로그인한 세션이 아니다 → 401. */
    public static class LoginRequired extends RuntimeException {
        public LoginRequired() {
            super("로그인이 필요해요");
        }
    }

    /** 아이디 또는 비밀번호가 틀렸다 → 401. 어느 쪽이 틀렸는지는 알려 주지 않는다. */
    public static class BadCredentials extends RuntimeException {
        public BadCredentials() {
            super("아이디 또는 비밀번호가 맞지 않아요");
        }
    }

    /** 이미 쓰는 아이디 → 409. */
    public static class DuplicateLoginId extends RuntimeException {
        public DuplicateLoginId() {
            super("이미 쓰고 있는 아이디예요");
        }
    }

    /** 이 브라우저 UUID 에 이미 계정이 붙어 있다 → 409. */
    public static class AlreadyRegistered extends RuntimeException {
        public AlreadyRegistered() {
            super("이미 계정이 있어요. 로그인해 주세요");
        }
    }

    @ExceptionHandler({LoginRequired.class, BadCredentials.class})
    ResponseEntity<Map<String, String>> unauthorized(RuntimeException e) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("message", e.getMessage()));
    }

    @ExceptionHandler({DuplicateLoginId.class, AlreadyRegistered.class})
    ResponseEntity<Map<String, String>> conflict(RuntimeException e) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of("message", e.getMessage()));
    }
}
