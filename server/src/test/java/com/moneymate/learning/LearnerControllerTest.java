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
}
