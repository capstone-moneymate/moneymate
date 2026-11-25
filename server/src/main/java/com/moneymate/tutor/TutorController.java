package com.moneymate.tutor;

import com.moneymate.auth.AuthController;
import com.moneymate.auth.UserGuard;
import com.moneymate.tutor.TutorDtos.TutorState;
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
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.SessionAttribute;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClientException;

/**
 * 튜터 에이전트 API (사람1, #240). 카드 개념 단계 화면(개념 단계 퀴즈 화면 A·B)이 부른다.
 * 튜터는 채점 서버(worker/tutor/api.py)가 돌리고, 여기서는 userId 를 확인한 뒤 그대로 전달한다 (LearnerController 와 같다).
 * 채점 서버가 꺼져 있거나 시간이 넘으면 503 과 {"message": ...}. 화면은 개념 단계를 건너뛰고 본 문제로 가면 된다.
 */
@RestController
@RequestMapping("/api/tutor")
public class TutorController {

    private static final Logger log = LoggerFactory.getLogger(TutorController.class);

    private final TutorClient client;
    private final UserGuard guard;

    public TutorController(TutorClient client, UserGuard guard) {
        this.client = client;
        this.guard = guard;
    }

    /** 카드의 개념 단계 튜터를 시작한다. 첫 퀴즈(또는 설명·끝)까지의 이벤트를 돌려준다 */
    @PostMapping("/start")
    public TutorState start(@Valid @RequestBody StartRequest request,
                            @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return client.start(guard.check(request.userId(), sessionUserId), request.cardId());
    }

    /** 기다리는 퀴즈의 답. 채점(정답·해설 포함)과 다음 퀴즈(또는 끝)까지의 이벤트를 돌려준다 */
    @PostMapping("/{sessionId}/answer")
    public TutorState answer(@PathVariable String sessionId, @Valid @RequestBody AnswerRequest request,
                             @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return client.answer(sessionId, guard.check(request.userId(), sessionUserId), request.answer(),
                request.confidence(), request.responseMs(), request.answerChanges());
    }

    /** 지금 상태와 지금까지의 이벤트 전부 (화면을 새로 열었을 때) */
    @GetMapping("/{sessionId}")
    public TutorState get(@PathVariable String sessionId, @RequestParam UUID userId,
                          @SessionAttribute(name = AuthController.SESSION_USER_ID, required = false) String sessionUserId) {
        return client.get(sessionId, guard.check(userId, sessionUserId));
    }

    public record StartRequest(@NotNull UUID userId, @NotNull Long cardId) {
    }

    /**
     * @param answer        보기 고르기는 보기 번호(0부터), 칩 빈칸·짝 맞추기·사례 분류는 번호 목록 (TutorClient.answer 참고)
     * @param confidence    1 헷갈려요, 2 확실해요. 없으면 비움
     * @param responseMs    퀴즈가 화면에 뜬 순간부터 낼 때까지 (ms)
     * @param answerChanges 내기 전에 답을 바꾼 횟수
     */
    public record AnswerRequest(
            @NotNull UUID userId,
            @NotNull Object answer,
            @Min(1) @Max(2) Integer confidence,
            @PositiveOrZero Integer responseMs,
            @PositiveOrZero Integer answerChanges) {
    }

    /** 채점 서버가 거절했다: 없는 카드·세션(404), 기다리는 퀴즈가 없음(409), 그 밖은 잘못된 요청(400) */
    @ExceptionHandler(HttpClientErrorException.class)
    ResponseEntity<Map<String, String>> tutorServerRejected(HttpClientErrorException e) {
        int code = e.getStatusCode().value();
        if (code == HttpStatus.NOT_FOUND.value()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", "튜터를 찾을 수 없어요. 본 문제로 넘어가 주세요."));
        }
        if (code == HttpStatus.CONFLICT.value()) {
            return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of("message", "앞의 답을 처리하고 있거나 기다리는 퀴즈가 없어요."));
        }
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("message", "요청을 확인해 주세요."));
    }

    @ExceptionHandler(RestClientException.class)
    ResponseEntity<Map<String, String>> tutorServerDown(RestClientException e) {
        log.warn("튜터를 부르지 못했어요: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("message", "튜터를 잠시 쓸 수 없어요. 본 문제로 넘어가 주세요."));
    }
}
