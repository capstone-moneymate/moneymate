package com.moneymate.auth;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.moneymate.mypage.MypageController;
import com.moneymate.mypage.MypageDtos.Summary;
import com.moneymate.mypage.MypageService;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * 가입 → 세션 → 다른 API(마이페이지)의 UserGuard 까지 HTTP 로 확인한다. DB 는 가짜.
 * 계정에 붙은 UUID 는 그 계정 세션에서만 쓸 수 있고, 익명 UUID 는 지금처럼 그대로 쓴다.
 */
class AuthFlowTest {

    static final String ACCOUNT = "99999999-8888-7777-6666-555555555555";
    static final String ANON = "11111111-2222-3333-4444-555555555555";

    AuthRepository repo;
    MypageService mypage;
    MockMvc mvc;

    @BeforeEach
    void setUp() {
        repo = mock(AuthRepository.class);
        mypage = mock(MypageService.class);
        when(repo.findLoginId(anyString())).thenReturn(Optional.empty());
        when(repo.findLoginId(ACCOUNT)).thenReturn(Optional.of("yerin_01"));
        when(repo.findByLoginId(anyString())).thenReturn(Optional.empty());
        when(mypage.summary(anyString())).thenReturn(new Summary(0, false, 0, null, 0, 0));

        BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(4);
        when(repo.findByLoginId("yerin_01"))
                .thenReturn(Optional.of(new AuthRepository.Account(ACCOUNT, "yerin_01", encoder.encode("password123"))));
        UserGuard guard = new UserGuard(repo);
        mvc = MockMvcBuilders
                .standaloneSetup(new AuthController(new AuthService(repo, encoder)), new MypageController(mypage, guard))
                .setControllerAdvice(new AuthExceptions())
                .build();
    }

    @Test
    void 익명_UUID_는_로그인_없이_그대로_쓴다() throws Exception {
        mvc.perform(get("/api/mypage/summary").param("userId", ANON)).andExpect(status().isOk());
    }

    @Test
    void 계정_UUID_를_세션_없이_보내면_401() throws Exception {
        mvc.perform(get("/api/mypage/summary").param("userId", ACCOUNT))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.message").value("로그인이 필요해요"));
    }

    @Test
    void 로그인한_세션이면_계정_UUID_를_쓴다() throws Exception {
        MockHttpSession session = new MockHttpSession();
        mvc.perform(post("/api/auth/login").session(session).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"loginId\":\"yerin_01\",\"password\":\"password123\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(ACCOUNT));

        mvc.perform(get("/api/mypage/summary").param("userId", ACCOUNT).session(session))
                .andExpect(status().isOk());
        mvc.perform(get("/api/auth/me").session(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.loginId").value("yerin_01"));
    }

    @Test
    void 다른_계정으로_로그인한_세션이어도_남의_계정_UUID_는_401() throws Exception {
        String other = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
        when(repo.findLoginId(other)).thenReturn(Optional.of("someone"));
        MockHttpSession session = new MockHttpSession();
        session.setAttribute(AuthController.SESSION_USER_ID, ACCOUNT);

        mvc.perform(get("/api/mypage/summary").param("userId", other).session(session))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 로그아웃하면_세션이_끊긴다() throws Exception {
        MockHttpSession session = new MockHttpSession();
        session.setAttribute(AuthController.SESSION_USER_ID, ACCOUNT);

        mvc.perform(post("/api/auth/logout").session(session)).andExpect(status().isNoContent());
        mvc.perform(get("/api/auth/me")).andExpect(status().isUnauthorized());
    }

    @Test
    void 틀린_비밀번호는_401_메시지() throws Exception {
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"loginId\":\"yerin_01\",\"password\":\"nope-nope\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.message").value("아이디 또는 비밀번호가 맞지 않아요"));
    }

    @Test
    void 아이디_형식이_틀리면_400_메시지() throws Exception {
        mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"userId\":\"" + ANON + "\",\"loginId\":\"AB\",\"password\":\"password123\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("아이디는 영문 소문자·숫자·_ 4~20자로 써 주세요"));
    }

    @Test
    void 가입하면_바로_로그인_상태() throws Exception {
        when(repo.attachLogin(eq(ANON), eq("newbie_1"), anyString())).thenReturn(1);
        MockHttpSession session = new MockHttpSession();

        mvc.perform(post("/api/auth/signup").session(session).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"userId\":\"" + ANON + "\",\"loginId\":\"newbie_1\",\"password\":\"password123\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(ANON));
        // 가입 뒤에는 이 UUID 가 계정이 된다
        when(repo.findLoginId(ANON)).thenReturn(Optional.of("newbie_1"));

        mvc.perform(get("/api/mypage/summary").param("userId", ANON).session(session)).andExpect(status().isOk());
        mvc.perform(get("/api/mypage/summary").param("userId", ANON)).andExpect(status().isUnauthorized());
    }
}
