package com.moneymate.answer;

import com.moneymate.auth.AuthController;
import com.moneymate.auth.UserGuard;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.SessionAttribute;

/**
 * 고스트 비교 (계획 2-6). 같은 카드를 다시 풀 때 지난번 기록과 이번 기록을 단계별로 나란히 놓는다. DB 읽기만 한다.
 * 계산은 {@link Ghost}, 응답 모양은 {@link GhostDtos}.
 */
@RestController
public class GhostController {

    private final GhostRepository repository;
    private final UserGuard guard;

    public GhostController(GhostRepository repository, UserGuard guard) {
        this.repository = repository;
        this.guard = guard;
    }

    /** 이 카드의 지난 기록(lastComplete)과 가장 최근 시도의 비교(comparison). 풀어 본 적이 없으면 둘 다 null. */
    @GetMapping("/api/answers/ghost")
    public GhostDtos.Report ghost(@RequestParam UUID userId,
                                  @RequestParam long cardId,
                                  @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        String id = guard.check(userId, sessionUserId);
        return Ghost.report(repository.findSteps(cardId), repository.findRows(id, cardId));
    }
}
