package com.moneymate.learning;

import com.moneymate.auth.AuthController;
import com.moneymate.auth.UserGuard;
import com.moneymate.learning.LearnerDtos.Calibration;
import com.moneymate.learning.LearnerDtos.ReviewQueue;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.SessionAttribute;
import org.springframework.web.client.RestClientException;

/**
 * 학습자 상태 조회 API (사람2, docs/추가구현_계획.md 2-7). 마이페이지의 "오늘의 복습"과 "확신 점검"이 부른다.
 * 계산은 채점 서버(worker/learner)가 하고, 여기서는 userId 를 확인한 뒤 그대로 전달한다.
 * 채점 서버가 꺼져 있거나 실패하면 503 과 {"message": ...}.
 */
@RestController
@RequestMapping("/api/learner")
public class LearnerController {

    private static final Logger log = LoggerFactory.getLogger(LearnerController.class);

    private final LearnerStateClient client;
    private final UserGuard guard;

    public LearnerController(LearnerStateClient client, UserGuard guard) {
        this.client = client;
        this.guard = guard;
    }

    /** 오늘 복습할 개념: 확실해요인데 틀린 개념 먼저, 나머지는 기억 확률 낮은 순, 하루 상한까지. */
    @GetMapping("/reviews")
    public ReviewQueue reviews(@RequestParam UUID userId,
                               @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return client.reviews(guard.check(userId, sessionUserId));
    }

    /** 확신 보정: 정답/오답 × 확실/헷갈려요 2 × 2 표와 지표 (전체, 최근 30일, 그 전). */
    @GetMapping("/calibration")
    public Calibration calibration(@RequestParam UUID userId,
                                   @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return client.calibration(guard.check(userId, sessionUserId));
    }

    @ExceptionHandler(RestClientException.class)
    ResponseEntity<Map<String, String>> learnerServerDown(RestClientException e) {
        log.warn("학습자 상태를 읽지 못했어요: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("message", "학습 상태를 잠시 불러올 수 없어요."));
    }
}
