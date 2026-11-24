package com.moneymate.learning;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.moneymate.auth.AuthExceptions;
import com.moneymate.auth.UserGuard;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.RestClientException;

/** LearnerController 테스트. 채점 서버(LearnerStateClient)와 UserGuard 는 가짜로 바꾼다. */
class LearnerControllerTest {

    static final UUID USER = UUID.fromString("11111111-2222-3333-4444-555555555555");

    LearnerStateClient client;
    UserGuard guard;
    LearnerController controller;

    @BeforeEach
    void setUp() {
        client = mock(LearnerStateClient.class);
        guard = mock(UserGuard.class);
        controller = new LearnerController(client, guard);
        when(guard.check(USER, null)).thenReturn(USER.toString());
    }

    @Test
    void reviewsPassThroughForCheckedUser() {
        LearnerDtos.ReviewQueue queue = new LearnerDtos.ReviewQueue(5, 0, 1, List.of(
                new LearnerDtos.ReviewItem(3L, "EPS", 0.4, 0.81, "sure_wrong", "2026-11-24T00:00:00Z")));
        when(client.reviews(USER.toString())).thenReturn(queue);

        assertThat(controller.reviews(USER, null)).isSameAs(queue);
    }

    @Test
    void calibrationPassThroughForCheckedUser() {
        LearnerDtos.CalibrationSummary none = new LearnerDtos.CalibrationSummary(
                0, false, 0, 0, 0, 0, null, null, null, null, null, null, null, null);
        LearnerDtos.Calibration calibration = new LearnerDtos.Calibration(none, none, none, 30, List.of());
        when(client.calibration(USER.toString())).thenReturn(calibration);

        assertThat(controller.calibration(USER, null)).isSameAs(calibration);
    }

    @Test
    void accountUserWithoutLoginNeverReachesLearnerServer() {
        // 계정에 붙은 UUID 인데 로그인 세션이 없으면 UserGuard 가 막는다 → 채점 서버를 부르지 않는다
        when(guard.check(USER, null)).thenThrow(new AuthExceptions.LoginRequired());

        assertThatThrownBy(() -> controller.reviews(USER, null)).isInstanceOf(AuthExceptions.LoginRequired.class);
        assertThatThrownBy(() -> controller.calibration(USER, null)).isInstanceOf(AuthExceptions.LoginRequired.class);
        verify(client, never()).reviews(any());
        verify(client, never()).calibration(any());
    }

    @Test
    void learnerServerFailureBecomes503WithMessage() {
        var response = controller.learnerServerDown(new RestClientException("connection refused"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
        assertThat(response.getBody()).containsKey("message");
    }

    // --- 복습 문제 풀기 ---

    @Test
    void reviewQuizAndAnswerPassThroughForCheckedUser() {
        LearnerDtos.ReviewQuiz quiz = new LearnerDtos.ReviewQuiz(9L, 3L, "EPS", "O/X",
                java.util.Map.of("statement", "문장", "options", List.of("O", "X")), 0.5);
        LearnerDtos.ReviewResult result = new LearnerDtos.ReviewResult(true, 0, "해설", "EPS", 0.65,
                "2026-11-26T09:00:00Z");
        when(client.reviewQuiz(USER.toString(), 3L)).thenReturn(quiz);
        when(client.reviewAnswer(USER.toString(), 9L, 0, 2, 4200, 1)).thenReturn(result);

        assertThat(controller.reviewQuiz(new LearnerController.ReviewQuizRequest(USER, 3L), null)).isSameAs(quiz);
        assertThat(controller.reviewAnswer(new LearnerController.ReviewAnswerRequest(USER, 9L, 0, 2, 4200, 1), null))
                .isSameAs(result);
    }

    @Test
    void reviewNeedsLoginForAccountUser() {
        when(guard.check(USER, null)).thenThrow(new AuthExceptions.LoginRequired());

        assertThatThrownBy(() -> controller.reviewQuiz(new LearnerController.ReviewQuizRequest(USER, 3L), null))
                .isInstanceOf(AuthExceptions.LoginRequired.class);
        assertThatThrownBy(() -> controller.reviewAnswer(
                new LearnerController.ReviewAnswerRequest(USER, 9L, 0, 2, null, null), null))
                .isInstanceOf(AuthExceptions.LoginRequired.class);
        verify(client, never()).reviewQuiz(any(), org.mockito.ArgumentMatchers.anyLong());
    }

    @Test
    void learnerServerRejectionKeepsItsMeaning() {
        assertThat(controller.learnerServerRejected(rejected(HttpStatus.NOT_FOUND)).getStatusCode())
                .isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(controller.learnerServerRejected(rejected(HttpStatus.CONFLICT)).getStatusCode())
                .isEqualTo(HttpStatus.CONFLICT);
        var bad = controller.learnerServerRejected(rejected(HttpStatus.valueOf(422)));
        assertThat(bad.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(bad.getBody()).containsKey("message");
    }

    static org.springframework.web.client.HttpClientErrorException rejected(HttpStatus status) {
        return org.springframework.web.client.HttpClientErrorException.create(
                status, status.getReasonPhrase(), new org.springframework.http.HttpHeaders(), new byte[0], null);
    }
}
