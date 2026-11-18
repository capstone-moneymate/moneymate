package com.moneymate.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.moneymate.auth.AuthDtos.LoginRequest;
import com.moneymate.auth.AuthDtos.Me;
import com.moneymate.auth.AuthDtos.SignupRequest;
import com.moneymate.auth.AuthRepository.Account;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/** AuthService 테스트. DB(AuthRepository)는 가짜, BCrypt 는 진짜를 쓴다. */
class AuthServiceTest {

    static final UUID ANON = UUID.fromString("11111111-2222-3333-4444-555555555555");
    static final String ANON_ID = ANON.toString();

    AuthRepository repo;
    PasswordEncoder encoder;
    AuthService service;

    @BeforeEach
    void setUp() {
        repo = mock(AuthRepository.class);
        encoder = new BCryptPasswordEncoder(4); // 테스트는 빠르게
        service = new AuthService(repo, encoder);
        when(repo.findLoginId(anyString())).thenReturn(Optional.empty());
        when(repo.findByLoginId(anyString())).thenReturn(Optional.empty());
    }

    @Test
    void 가입하면_지금_UUID_에_아이디와_해시를_붙인다() {
        when(repo.attachLogin(eq(ANON_ID), eq("yerin_01"), anyString())).thenReturn(1);

        Me me = service.signup(new SignupRequest(ANON, "yerin_01", "password123"));

        assertThat(me).isEqualTo(new Me(ANON_ID, "yerin_01"));
        verify(repo).ensureUser(ANON_ID);
        ArgumentCaptor<String> hash = ArgumentCaptor.forClass(String.class);
        verify(repo).attachLogin(eq(ANON_ID), eq("yerin_01"), hash.capture());
        assertThat(hash.getValue()).isNotEqualTo("password123").startsWith("$2");
        assertThat(encoder.matches("password123", hash.getValue())).isTrue();
    }

    @Test
    void 이미_계정인_UUID_로_가입하면_409() {
        when(repo.findLoginId(ANON_ID)).thenReturn(Optional.of("other"));

        assertThatThrownBy(() -> service.signup(new SignupRequest(ANON, "yerin_01", "password123")))
                .isInstanceOf(AuthExceptions.AlreadyRegistered.class);
        verify(repo, never()).attachLogin(anyString(), anyString(), anyString());
    }

    @Test
    void 이미_있는_아이디면_409() {
        when(repo.findByLoginId("yerin_01")).thenReturn(Optional.of(new Account("x", "yerin_01", "h")));

        assertThatThrownBy(() -> service.signup(new SignupRequest(ANON, "yerin_01", "password123")))
                .isInstanceOf(AuthExceptions.DuplicateLoginId.class);
    }

    @Test
    void 동시에_같은_아이디로_가입해_UNIQUE_위반이면_409() {
        when(repo.attachLogin(eq(ANON_ID), eq("yerin_01"), anyString())).thenThrow(new DuplicateKeyException("dup"));

        assertThatThrownBy(() -> service.signup(new SignupRequest(ANON, "yerin_01", "password123")))
                .isInstanceOf(AuthExceptions.DuplicateLoginId.class);
    }

    @Test
    void 비밀번호가_맞으면_그_계정으로_로그인() {
        String account = "99999999-8888-7777-6666-555555555555";
        when(repo.findByLoginId("yerin_01"))
                .thenReturn(Optional.of(new Account(account, "yerin_01", encoder.encode("password123"))));

        assertThat(service.login(new LoginRequest("yerin_01", "password123"))).isEqualTo(new Me(account, "yerin_01"));
    }

    @Test
    void 비밀번호가_틀리거나_없는_아이디면_같은_401() {
        when(repo.findByLoginId("yerin_01"))
                .thenReturn(Optional.of(new Account("x", "yerin_01", encoder.encode("password123"))));

        assertThatThrownBy(() -> service.login(new LoginRequest("yerin_01", "wrong-pass")))
                .isInstanceOf(AuthExceptions.BadCredentials.class);
        assertThatThrownBy(() -> service.login(new LoginRequest("nobody", "password123")))
                .isInstanceOf(AuthExceptions.BadCredentials.class)
                .hasMessage("아이디 또는 비밀번호가 맞지 않아요");
    }
}
