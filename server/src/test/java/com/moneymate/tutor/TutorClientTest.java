package com.moneymate.tutor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.moneymate.tutor.TutorDtos.TutorState;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;

/** TutorClient 가 worker/tutor/api.py 와 같은 JSON 을 주고받는지 (가짜 서버). */
class TutorClientTest {

    static final String USER = "11111111-2222-3333-4444-555555555555";
    static final String STATE = """
            {"session_id":"abc","status":"waiting","finished_by":null,"targets":["자사주 소각"],"quizzes":1,"max_quizzes":6,
             "events":[{"type":"explain","concept":"자기주식","style":"예시 위주","text":"설명"},
                       {"type":"quiz","kind":"용어 뜻","concept":"자기주식","content":{"question":"?","options":["a","b","c"]},"guess_p":0.333}]}""";

    MockRestServiceServer server;
    TutorClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://judge");
        server = MockRestServiceServer.bindTo(builder).build();
        client = new TutorClient(builder.build());
    }

    @Test
    void startSendsSnakeCaseAndReadsState() {
        server.expect(requestTo("http://judge/tutor/start"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().json("{\"user_id\":\"" + USER + "\",\"card_id\":17}"))
                .andRespond(withSuccess(STATE, MediaType.APPLICATION_JSON));

        TutorState s = client.start(USER, 17L);
        assertThat(s.sessionId()).isEqualTo("abc");
        assertThat(s.maxQuizzes()).isEqualTo(6);
        assertThat(s.targets()).containsExactly("자사주 소각");
        assertThat(s.events()).hasSize(2);
        assertThat(s.events().get(1)).containsEntry("type", "quiz").doesNotContainKey("key");
        server.verify();
    }

    @Test
    void answerSendsListAnswerAndOptionalFields() {
        server.expect(requestTo("http://judge/tutor/abc/answer"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().json("""
                        {"user_id":"11111111-2222-3333-4444-555555555555","answer":[0,1],"confidence":2,
                         "response_ms":4200,"answer_changes":1}"""))
                .andRespond(withSuccess(STATE.replace("waiting", "done"), MediaType.APPLICATION_JSON));

        assertThat(client.answer("abc", USER, List.of(0, 1), 2, 4200, 1).status()).isEqualTo("done");
        server.verify();
    }

    @Test
    void getPassesUserIdAsQuery() {
        server.expect(requestTo("http://judge/tutor/abc?user_id=" + USER))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess(STATE, MediaType.APPLICATION_JSON));

        assertThat(client.get("abc", USER).quizzes()).isEqualTo(1);
        server.verify();
    }

    @Test
    void rejectedSessionRaises() {
        server.expect(requestTo("http://judge/tutor/abc/answer")).andRespond(withStatus(HttpStatus.NOT_FOUND));

        assertThatThrownBy(() -> client.answer("abc", USER, 0, null, null, null))
                .isInstanceOf(HttpClientErrorException.NotFound.class);
        server.verify();
    }
}
