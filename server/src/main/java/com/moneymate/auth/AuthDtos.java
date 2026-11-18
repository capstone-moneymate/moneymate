package com.moneymate.auth;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.UUID;

/** 회원가입·로그인 API 의 요청과 응답. */
public final class AuthDtos {

    private AuthDtos() {
    }

    /**
     * POST /api/auth/signup.
     *
     * @param userId   지금 브라우저가 쓰는 익명 UUID. 이 UUID 에 계정을 붙여서 그동안의 학습 기록을 이어 간다
     * @param loginId  아이디: 영문 소문자·숫자·_ 4~20자
     * @param password 비밀번호: 8~64자
     */
    public record SignupRequest(
            @NotNull UUID userId,
            @NotBlank @Pattern(regexp = "[a-z0-9_]{4,20}", message = "아이디는 영문 소문자·숫자·_ 4~20자로 써 주세요") String loginId,
            @NotBlank @Size(min = 8, max = 64, message = "비밀번호는 8~64자로 써 주세요") String password) {
    }

    /** POST /api/auth/login. 형식 검사는 하지 않는다 (틀리면 그냥 "아이디 또는 비밀번호가 맞지 않아요"). */
    public record LoginRequest(@NotBlank String loginId, @NotBlank String password) {
    }

    /** 로그인한 계정. 웹은 userId 를 localStorage 에 넣고 기존 API 에 그대로 보낸다. */
    public record Me(String userId, String loginId) {
    }
}
