package com.moneymate.answer;

import com.moneymate.auth.AuthController;
import com.moneymate.auth.UserGuard;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.SessionAttribute;

/** 탭1 코드 채점 답안 API (퀴즈·차트 읽기·인과 순서). 판단해보기는 /api/judgement. */
@RestController
@RequestMapping("/api/answers")
public class AnswerController {

    private final AnswerService service;
    private final UserGuard guard;

    public AnswerController(AnswerService service, UserGuard guard) {
        this.service = service;
        this.guard = guard;
    }

    @PostMapping
    public AnswerResult submit(@Valid @RequestBody AnswerRequest request,
                               @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        guard.check(request.userId(), sessionUserId);
        return service.submit(request);
    }
}
