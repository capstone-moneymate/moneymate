package com.moneymate.learning;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

/** LearnerStateClient 가 worker/learner/api.py 의 AnswerIn 과 같은 JSON 을 보내는지 (가짜 서버). */
class LearnerStateClientTest {

    static final String USER = "11111111-2222-3333-4444-555555555555";

    MockRestServiceServer server;
    LearnerStateClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://judge");
        server = MockRestServiceServer.bindTo(builder).build();
        client = new LearnerStateClient(builder.build());
    }

    @Test
    void sendsSnakeCaseBody() {
        server.expect(requestTo("http://judge/learner/answer"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().json("""
                        {"user_id":"11111111-2222-3333-4444-555555555555","concept_ids":["rate_hold","bank_profit"],
                         "correct":true,"kind":"quiz","count":4}"""))
                .andRespond(withSuccess("{\"guess_p\":0.25,\"mastery\":{\"rate_hold\":0.65}}",
                        MediaType.APPLICATION_JSON));

        assertThat(client.recordAnswer(USER, new String[] {"rate_hold", "bank_profit"}, true, "quiz", 4)).isTrue();
        server.verify();
    }

    @Test
    void serverErrorIsSwallowed() {
        server.expect(requestTo("http://judge/learner/answer")).andRespond(withServerError());

        assertThat(client.recordAnswer(USER, new String[] {"rate_hold"}, false, "causal_order", 3)).isFalse();
        server.verify();
    }

    @Test
    void noConceptsMeansNoCall() {
        // 기대한 요청이 없으니, 부르면 MockRestServiceServer 가 실패시킨다
        assertThat(client.recordAnswer(USER, new String[] {}, true, "quiz", 4)).isFalse();
        assertThat(client.recordAnswer(USER, null, true, "quiz", 4)).isFalse();
        assertThat(client.recordAnswer(USER, new String[] {"rate_hold"}, true, "quiz", 0)).isFalse();
        server.verify();
    }
}
