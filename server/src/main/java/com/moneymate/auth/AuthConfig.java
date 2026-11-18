package com.moneymate.auth;

import jakarta.servlet.SessionCookieConfig;
import java.time.Duration;
import org.springframework.boot.web.server.servlet.CookieSameSiteSupplier;
import org.springframework.boot.web.servlet.ServletContextInitializer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * 로그인 세션 쿠키와 비밀번호 해시 설정.
 * application.yml(공통 파일)을 건드리지 않으려고 코드로 둔다.
 */
@Configuration
public class AuthConfig {

    /** 로그인 유지 기간. 쿠키 수명과 세션 유휴 시간을 같게 둔다 */
    public static final Duration LOGIN_TTL = Duration.ofDays(7);

    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    /** 세션 쿠키(JSESSIONID)에 SameSite=Lax. 다른 사이트에서 보낸 POST 에는 쿠키가 실리지 않는다 (CSRF 막기) */
    @Bean
    CookieSameSiteSupplier sessionCookieSameSite() {
        return CookieSameSiteSupplier.ofLax().whenHasName("JSESSIONID");
    }

    /**
     * 세션 쿠키를 브라우저를 닫아도 남게 한다 (HttpOnly 는 기본값).
     * 배포(HTTPS)에서는 SESSION_COOKIE_SECURE=true 로 Secure 를 붙인다.
     */
    @Bean
    ServletContextInitializer sessionCookieInitializer() {
        return servletContext -> {
            SessionCookieConfig cookie = servletContext.getSessionCookieConfig();
            cookie.setHttpOnly(true);
            cookie.setMaxAge((int) LOGIN_TTL.toSeconds());
            cookie.setSecure(Boolean.parseBoolean(System.getenv().getOrDefault("SESSION_COOKIE_SECURE", "false")));
        };
    }
}
