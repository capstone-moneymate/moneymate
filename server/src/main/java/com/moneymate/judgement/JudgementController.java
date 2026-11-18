package com.moneymate.judgement;

import com.moneymate.auth.AuthController;
import com.moneymate.auth.UserGuard;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.SessionAttribute;

/** 판단해보기 근거 채점 API. C의 판단해보기 화면이 부른다. */
@RestController
@RequestMapping("/api/judgement")
public class JudgementController {

    private final JudgementService service;
    private final UserGuard guard;

    public JudgementController(JudgementService service, UserGuard guard) {
        this.service = service;
        this.guard = guard;
    }

    @PostMapping
    public JudgementResponse judge(@Valid @RequestBody JudgementRequest request,
                                   @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        guard.check(request.userId(), sessionUserId);
        return service.judge(request);
    }

    /** "모르겠어요, 설명 볼래요": 카드의 낙관·비관 토론. 없으면 bull·bear 가 null */
    @GetMapping("/explanation")
    public JudgementExplanation explain(@RequestParam long stepId) {
        return service.explain(stepId);
    }
}
