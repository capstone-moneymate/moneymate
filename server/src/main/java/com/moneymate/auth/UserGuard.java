package com.moneymate.auth;

import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * 요청에 실린 userId 를 써도 되는지 확인한다.
 * <ul>
 *   <li>익명 UUID(계정이 안 붙은 UUID): 지금까지처럼 그대로 쓴다</li>
 *   <li>계정에 붙은 UUID: 그 계정으로 로그인한 세션에서 온 요청만 쓴다. 아니면 401</li>
 * </ul>
 * 그래서 다른 사람의 UUID 를 알아도 계정 기록은 보거나 바꿀 수 없다.
 * 컨트롤러에서 {@code @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false)} 로 세션 값을 받아 넘긴다.
 */
@Component
public class UserGuard {

    private final AuthRepository repository;

    public UserGuard(AuthRepository repository) {
        this.repository = repository;
    }

    /**
     * @param userId        요청의 userId (선택 값이면 null 일 수 있다)
     * @param sessionUserId 세션에 저장된 로그인 userId (로그인 안 했으면 null)
     * @return 써도 되는 userId 문자열. userId 가 null 이면 null
     */
    public String check(UUID userId, String sessionUserId) {
        if (userId == null) {
            return null;
        }
        String id = userId.toString();
        if (id.equals(sessionUserId)) {
            return id;
        }
        if (repository.findLoginId(id).isPresent()) {
            throw new AuthExceptions.LoginRequired();
        }
        return id;
    }
}
