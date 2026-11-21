package com.moneymate.answer;

import com.moneymate.auth.AuthController;
import com.moneymate.auth.UserGuard;
import jakarta.validation.Valid;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.SessionAttribute;

/**
 * 탭1 코드 채점 답안 API (퀴즈·차트 읽기·인과 순서). 판단해보기는 /api/judgement.
 * GET /history 는 탭3 "풀었던 내용 보기"가 부른다 (내가 낸 답과 채점 결과).
 */
@RestController
@RequestMapping("/api/answers")
public class AnswerController {

    private final AnswerService service;
    private final AnswerHistoryService history;
    private final UserGuard guard;

    public AnswerController(AnswerService service, AnswerHistoryService history, UserGuard guard) {
        this.service = service;
        this.history = history;
        this.guard = guard;
    }

    @PostMapping
    public AnswerResult submit(@Valid @RequestBody AnswerRequest request,
                               @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        guard.check(request.userId(), sessionUserId);
        return service.submit(request);
    }

    /** 이 카드에서 내가 낸 답과 채점 결과 (단계 번호 순). date(yyyy-MM-dd, KST)를 주면 그날 마지막 답안. 없으면 빈 배열. */
    @GetMapping("/history")
    public List<PastAnswer> history(@RequestParam UUID userId,
                                    @RequestParam long cardId,
                                    @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date,
                                    @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return history.history(guard.check(userId, sessionUserId), cardId, date);
    }
}
