package com.moneymate.auth;

import com.moneymate.auth.AuthDtos.LoginRequest;
import com.moneymate.auth.AuthDtos.Me;
import com.moneymate.auth.AuthDtos.SignupRequest;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.SessionAttribute;

/**
 * 회원가입·로그인·로그아웃 API (가벼운 세션 방식, docs/modules/auth_api.md).
 * 로그인하면 서버 세션에 userId 를 넣고, 브라우저에는 세션 쿠키(JSESSIONID)만 간다.
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    /** 세션에 넣는 로그인 userId 의 이름. 다른 컨트롤러가 @SessionAttribute 로 읽는다 */
    public static final String SESSION_USER_ID = "moneymate.userId";

    private final AuthService service;

    public AuthController(AuthService service) {
        this.service = service;
    }

    /** 지금 브라우저의 익명 UUID 에 계정을 붙이고, 바로 로그인 상태로 만든다. */
    @PostMapping("/signup")
    public Me signup(@Valid @RequestBody SignupRequest request, HttpServletRequest http) {
        Me me = service.signup(request);
        startSession(http, me);
        return me;
    }

    @PostMapping("/login")
    public Me login(@Valid @RequestBody LoginRequest request, HttpServletRequest http) {
        Me me = service.login(request);
        startSession(http, me);
        return me;
    }

    /** 세션을 끊는다. 로그인 안 한 상태에서 불러도 204. */
    @PostMapping("/logout")
    public ResponseEntity<Void> logout(HttpServletRequest http) {
        HttpSession session = http.getSession(false);
        if (session != null) {
            session.invalidate();
        }
        return ResponseEntity.noContent().build();
    }

    /** 지금 로그인한 계정. 로그인 안 했으면 401. 웹은 앱을 열 때 이것으로 로그인이 살아 있는지 본다. */
    @GetMapping("/me")
    public Me me(@SessionAttribute(name = SESSION_USER_ID, required = false) String sessionUserId) {
        if (sessionUserId == null) {
            throw new AuthExceptions.LoginRequired();
        }
        return service.me(sessionUserId).orElseThrow(AuthExceptions.LoginRequired::new);
    }

    /** 세션 고정 공격을 막으려고 로그인할 때마다 세션 id 를 새로 받는다. */
    private static void startSession(HttpServletRequest http, Me me) {
        http.getSession(true);
        http.changeSessionId();
        HttpSession session = http.getSession(false);
        session.setAttribute(SESSION_USER_ID, me.userId());
        session.setMaxInactiveInterval((int) AuthConfig.LOGIN_TTL.toSeconds());
    }

    /** 형식 검사 실패 → 400, 웹이 그대로 보여 줄 수 있게 첫 메시지 하나만. */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<Map<String, String>> invalid(MethodArgumentNotValidException e) {
        FieldError error = e.getBindingResult().getFieldError();
        String message = error != null && error.getDefaultMessage() != null
                ? error.getDefaultMessage() : "입력값을 확인해 주세요";
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("message", message));
    }
}
