package com.moneymate.auth;

import java.util.Optional;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/** 계정 DB 접근 (MyBatis). SQL 은 resources/mapper/auth/AuthRepository.xml */
@Mapper
public interface AuthRepository {

    /** 아이디로 계정 찾기. 없으면 빈 값. */
    Optional<Account> findByLoginId(@Param("loginId") String loginId);

    /** 이 UUID 에 붙은 아이디. 익명 사용자이거나 users 에 없으면 빈 값. */
    Optional<String> findLoginId(@Param("userId") String userId);

    /** users 에 없으면 넣는다 (아직 문제를 안 푼 익명 사용자도 가입할 수 있게). */
    void ensureUser(@Param("userId") String userId);

    /**
     * 익명 사용자에게 아이디·비밀번호 해시를 붙인다. 이미 계정인 UUID 면 바꾸지 않는다.
     *
     * @return 바뀐 행 수 (0 이면 이미 계정인 UUID)
     */
    int attachLogin(@Param("userId") String userId,
                    @Param("loginId") String loginId,
                    @Param("passwordHash") String passwordHash);

    /** users 한 행 중 로그인에 필요한 값. */
    record Account(String userId, String loginId, String passwordHash) {
    }
}
