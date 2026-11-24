package com.moneymate.learning;

import com.moneymate.auth.AuthController;
import com.moneymate.auth.UserGuard;
import com.moneymate.learning.LearnerDtos.Calibration;
import com.moneymate.learning.LearnerDtos.ReviewQueue;
import com.moneymate.learning.LearnerDtos.ReviewQuiz;
import com.moneymate.learning.LearnerDtos.ReviewResult;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.SessionAttribute;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClientException;

/**
 * 학습자 상태 API (사람2, docs/추가구현_계획.md 2-7). 마이페이지의 "오늘의 복습"·"확신 점검"과 복습 문제 풀기가 부른다.
 * 계산·출제·채점은 채점 서버(worker/learner)가 하고, 여기서는 userId 를 확인한 뒤 그대로 전달한다.
 * 채점 서버가 꺼져 있거나 실패하면 503 과 {"message": ...}. 채점 서버가 4xx 로 거절하면 404·409·400 으로 전한다.
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

    /** 복습할 개념의 문제 하나. 정답은 내려가지 않는다. 오늘 복습할 개념이 아니면 409 */
    @PostMapping("/review/quiz")
    public ReviewQuiz reviewQuiz(@Valid @RequestBody ReviewQuizRequest request,
                                 @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return client.reviewQuiz(guard.check(request.userId(), sessionUserId), request.nodeId());
    }

    /** 복습 문제 답 채점. 알 확률과 복습 일정이 바뀌고, 정답·해설·다음 복습일을 돌려준다. 이미 답한 문제면 409 */
    @PostMapping("/review/answer")
    public ReviewResult reviewAnswer(@Valid @RequestBody ReviewAnswerRequest request,
                                     @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return client.reviewAnswer(guard.check(request.userId(), sessionUserId), request.quizId(), request.answer(),
                request.confidence(), request.responseMs(), request.answerChanges());
    }

    /** @param nodeId 복습할 개념 (GET /api/learner/reviews 의 nodeId) */
    public record ReviewQuizRequest(@NotNull UUID userId, @NotNull Long nodeId) {
    }

    /**
     * @param answer        고른 보기 번호 (0부터)
     * @param confidence    정답을 보기 전에 누른 확신: 1 헷갈려요, 2 확실해요
     * @param responseMs    문제가 화면에 뜬 순간부터 낼 때까지 (ms)
     * @param answerChanges 내기 전에 답을 바꾼 횟수
     */
    public record ReviewAnswerRequest(
            @NotNull UUID userId,
            @NotNull Long quizId,
            @NotNull Object answer,
            @Min(1) @Max(2) Integer confidence,
            @PositiveOrZero Integer responseMs,
            @PositiveOrZero Integer answerChanges) {
    }

    /** 채점 서버가 요청을 거절했다: 없는 문제(404), 이미 답했거나 오늘 복습할 개념이 아님(409), 그 밖은 잘못된 요청(400) */
    @ExceptionHandler(HttpClientErrorException.class)
    ResponseEntity<Map<String, String>> learnerServerRejected(HttpClientErrorException e) {
        int code = e.getStatusCode().value();
        if (code == HttpStatus.NOT_FOUND.value()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", "없는 복습 문제예요."));
        }
        if (code == HttpStatus.CONFLICT.value()) {
            return ResponseEntity.status(HttpStatus.CONFLICT)
                    .body(Map.of("message", "이미 풀었거나 오늘 복습할 개념이 아니에요."));
        }
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("message", "요청을 확인해 주세요."));
    }

    @ExceptionHandler(RestClientException.class)
    ResponseEntity<Map<String, String>> learnerServerDown(RestClientException e) {
        log.warn("학습자 상태를 읽지 못했어요: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("message", "학습 상태를 잠시 불러올 수 없어요."));
    }
}
