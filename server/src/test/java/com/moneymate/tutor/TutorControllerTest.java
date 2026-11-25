package com.moneymate.tutor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.moneymate.auth.AuthExceptions;
import com.moneymate.auth.UserGuard;
import com.moneymate.tutor.TutorDtos.TutorState;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClientException;

/** TutorController 테스트. 채점 서버(TutorClient)와 UserGuard 는 가짜로 바꾼다. */
class TutorControllerTest {

    static final UUID USER = UUID.fromString("11111111-2222-3333-4444-555555555555");
    static final TutorState STATE = new TutorState("abc", "waiting", null, List.of("자사주 소각"), 1, 6,
            List.of(Map.of("type", "quiz")));

    TutorClient client;
    UserGuard guard;
    TutorController controller;

    @BeforeEach
    void setUp() {
        client = mock(TutorClient.class);
        guard = mock(UserGuard.class);
        controller = new TutorController(client, guard);
        when(guard.check(USER, null)).thenReturn(USER.toString());
    }

    @Test
    void startAnswerGetPassThroughForCheckedUser() {
        when(client.start(USER.toString(), 17L)).thenReturn(STATE);
        when(client.answer("abc", USER.toString(), 0, 2, 3000, 0)).thenReturn(STATE);
        when(client.get("abc", USER.toString())).thenReturn(STATE);

        assertThat(controller.start(new TutorController.StartRequest(USER, 17L), null)).isSameAs(STATE);
        assertThat(controller.answer("abc", new TutorController.AnswerRequest(USER, 0, 2, 3000, 0), null)).isSameAs(STATE);
        assertThat(controller.get("abc", USER, null)).isSameAs(STATE);
    }

    @Test
    void accountUserWithoutLoginNeverReachesTutorServer() {
        when(guard.check(USER, null)).thenThrow(new AuthExceptions.LoginRequired());

        assertThatThrownBy(() -> controller.start(new TutorController.StartRequest(USER, 17L), null))
                .isInstanceOf(AuthExceptions.LoginRequired.class);
        verify(client, never()).start(any(), anyLong());
    }

    @Test
    void rejectionsMapToStatus() {
        var notFound = controller.tutorServerRejected(HttpClientErrorException.create(HttpStatus.NOT_FOUND, "nf",
                HttpHeaders.EMPTY, new byte[0], StandardCharsets.UTF_8));
        var conflict = controller.tutorServerRejected(HttpClientErrorException.create(HttpStatus.CONFLICT, "c",
                HttpHeaders.EMPTY, new byte[0], StandardCharsets.UTF_8));
        var bad = controller.tutorServerRejected(HttpClientErrorException.create(HttpStatus.UNPROCESSABLE_ENTITY, "u",
                HttpHeaders.EMPTY, new byte[0], StandardCharsets.UTF_8));

        assertThat(notFound.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(conflict.getStatusCode()).isEqualTo(HttpStatus.CONFLICT);
        assertThat(bad.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(notFound.getBody()).containsKey("message");
    }

    @Test
    void tutorServerFailureBecomes503WithMessage() {
        var response = controller.tutorServerDown(new RestClientException("timeout"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
        assertThat(response.getBody()).containsKey("message");
    }
}
