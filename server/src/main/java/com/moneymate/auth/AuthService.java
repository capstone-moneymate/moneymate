package com.moneymate.auth;

import com.moneymate.auth.AuthDtos.LoginRequest;
import com.moneymate.auth.AuthDtos.Me;
import com.moneymate.auth.AuthDtos.SignupRequest;
import com.moneymate.auth.AuthRepository.Account;
import java.util.Optional;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** 회원가입·로그인. 세션은 컨트롤러가 다루고, 여기서는 계정만 확인한다. */
@Service
public class AuthService {

    private final AuthRepository repository;
    private final PasswordEncoder encoder;
    /** 없는 아이디로 로그인해도 BCrypt 비교를 한 번 해서, 응답 시간으로 아이디가 있는지 알 수 없게 한다 */
    private final String dummyHash;

    public AuthService(AuthRepository repository, PasswordEncoder encoder) {
        this.repository = repository;
        this.encoder = encoder;
        this.dummyHash = encoder.encode("moneymate-dummy-password");
    }

    /** 지금 브라우저의 익명 UUID 에 아이디·비밀번호를 붙인다. 그동안의 학습 기록은 그대로 이어진다. */
    @Transactional
    public Me signup(SignupRequest req) {
        String userId = req.userId().toString();
        if (repository.findLoginId(userId).isPresent()) {
            throw new AuthExceptions.AlreadyRegistered();
        }
        if (repository.findByLoginId(req.loginId()).isPresent()) {
            throw new AuthExceptions.DuplicateLoginId();
        }
        repository.ensureUser(userId);
        try {
            int changed = repository.attachLogin(userId, req.loginId(), encoder.encode(req.password()));
            if (changed == 0) {
                // 위에서 확인한 뒤 같은 UUID 로 동시에 가입한 경우
                throw new AuthExceptions.AlreadyRegistered();
            }
        } catch (DuplicateKeyException e) {
            // 위에서 확인한 뒤 같은 아이디로 동시에 가입한 경우
            throw new AuthExceptions.DuplicateLoginId();
        }
        return new Me(userId, req.loginId());
    }

    /** 아이디·비밀번호가 맞으면 그 계정. 틀리면 BadCredentials. */
    public Me login(LoginRequest req) {
        Optional<Account> account = repository.findByLoginId(req.loginId());
        String hash = account.map(Account::passwordHash).orElse(dummyHash);
        boolean matches = encoder.matches(req.password(), hash);
        if (account.isEmpty() || !matches) {
            throw new AuthExceptions.BadCredentials();
        }
        return new Me(account.get().userId(), account.get().loginId());
    }

    /** 세션의 userId 로 계정 정보를 다시 읽는다. 계정이 아니면 빈 값. */
    public Optional<Me> me(String userId) {
        return repository.findLoginId(userId).map(loginId -> new Me(userId, loginId));
    }
}
