package com.moneymate.mypage;

import com.moneymate.auth.AuthController;
import com.moneymate.auth.UserGuard;
import com.moneymate.mypage.MypageDtos.CausalMap;
import com.moneymate.mypage.MypageDtos.Review;
import com.moneymate.mypage.MypageDtos.Summary;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.SessionAttribute;

/**
 * 탭3 마이페이지 API. B의 탭3 화면(홈 숫자·인과 지도·다시 보는 개념)이 부른다.
 * userId 는 필수 UUID. 없거나 형식이 틀리면 Spring 이 400 을 돌려준다.
 */
@RestController
@RequestMapping("/api/mypage")
public class MypageController {

    private final MypageService service;
    private final UserGuard guard;

    public MypageController(MypageService service, UserGuard guard) {
        this.service = service;
        this.guard = guard;
    }

    /** 배운 개념 + 한쪽 끝이라도 배운 개념에 닿은 사전 연결. 기록이 없으면 빈 배열. */
    @GetMapping("/map")
    public CausalMap map(@RequestParam UUID userId,
                         @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return service.map(guard.check(userId, sessionUserId));
    }

    /** 다시 보는 개념: total > 0 전부, 정답률 낮은 순 → 푼 횟수 적은 순 → id 순. */
    @GetMapping("/review")
    public Review review(@RequestParam UUID userId,
                         @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return service.review(guard.check(userId, sessionUserId));
    }

    /** 홈 숫자: 연속 학습, 배운 개념 수, 종합 정답률, 판단해보기 횟수. 기록이 없으면 0 (정답률은 null). */
    @GetMapping("/summary")
    public Summary summary(@RequestParam UUID userId,
                           @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return service.summary(guard.check(userId, sessionUserId));
    }
}
