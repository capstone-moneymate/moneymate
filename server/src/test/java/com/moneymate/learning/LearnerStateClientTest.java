package com.moneymate.learning;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
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
import org.springframework.web.client.RestClientException;

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
                         "correct":true,"kind":"quiz","count":4,
                         "confidence":2,"response_ms":5300,"answer_changes":1}"""))
                .andRespond(withSuccess("{\"guess_p\":0.25,\"mastery\":{\"rate_hold\":0.65}}",
                        MediaType.APPLICATION_JSON));

        assertThat(client.recordAnswer(USER, new String[] {"rate_hold", "bank_profit"}, true, "quiz", 4,
                2, 5300, 1)).isTrue();
        server.verify();
    }

    @Test
    void serverErrorIsSwallowed() {
        server.expect(requestTo("http://judge/learner/answer")).andRespond(withServerError());

        assertThat(client.recordAnswer(USER, new String[] {"rate_hold"}, false, "causal_order", 3,
                null, null, null)).isFalse();
        server.verify();
    }

    @Test
    void noConceptsMeansNoCall() {
        // 기대한 요청이 없으니, 부르면 MockRestServiceServer 가 실패시킨다
        assertThat(client.recordAnswer(USER, new String[] {}, true, "quiz", 4, 2, 1000, 0)).isFalse();
        assertThat(client.recordAnswer(USER, null, true, "quiz", 4, 2, 1000, 0)).isFalse();
        assertThat(client.recordAnswer(USER, new String[] {"rate_hold"}, true, "quiz", 0, 2, 1000, 0)).isFalse();
        server.verify();
    }

    // --- 조회 (마이페이지, 추가 구현 2-7) ---

    @Test
    void reviewsAreReadFromSnakeCase() {
        server.expect(requestTo("http://judge/learner/reviews/" + USER))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess("""
                        {"limit":5,"done_today":1,"due_total":7,"items":[
                          {"node_id":3,"concept":"EPS","p_know":0.4,"retrievability":0.81,"reason":"sure_wrong",
                           "due_at":"2026-11-24T00:00:00Z"}]}""", MediaType.APPLICATION_JSON));

        LearnerDtos.ReviewQueue q = client.reviews(USER);

        assertThat(q.limit()).isEqualTo(5);
        assertThat(q.doneToday()).isEqualTo(1);
        assertThat(q.dueTotal()).isEqualTo(7);
        assertThat(q.items()).hasSize(1);
        LearnerDtos.ReviewItem item = q.items().get(0);
        assertThat(item.nodeId()).isEqualTo(3L);
        assertThat(item.concept()).isEqualTo("EPS");
        assertThat(item.pKnow()).isEqualTo(0.4);
        assertThat(item.retrievability()).isEqualTo(0.81);
        assertThat(item.reason()).isEqualTo("sure_wrong");
        assertThat(item.dueAt()).isEqualTo("2026-11-24T00:00:00Z");
        server.verify();
    }

    @Test
    void calibrationKeepsNullForMissingRatios() {
        String full = """
                {"total":20,"enough":true,"sure_right":9,"sure_wrong":3,"unsure_right":3,"unsure_wrong":5,
                 "sensitivity":0.75,"specificity":0.625,"illusion":0.375,"sure_accuracy":0.75,
                 "unsure_accuracy":0.375,"gap":0.375,"gamma":0.6667,"bias":0.0}""";
        String empty = """
                {"total":0,"enough":false,"sure_right":0,"sure_wrong":0,"unsure_right":0,"unsure_wrong":0,
                 "sensitivity":null,"specificity":null,"illusion":null,"sure_accuracy":null,
                 "unsure_accuracy":null,"gap":null,"gamma":null,"bias":null}""";
        server.expect(requestTo("http://judge/learner/calibration/" + USER))
                .andRespond(withSuccess("{\"all\":" + full + ",\"recent\":" + full + ",\"earlier\":" + empty
                        + ",\"recent_days\":30,\"sure_wrong_concepts\":[\"EPS\"]}", MediaType.APPLICATION_JSON));

        LearnerDtos.Calibration c = client.calibration(USER);

        assertThat(c.recentDays()).isEqualTo(30);
        assertThat(c.sureWrongConcepts()).containsExactly("EPS");
        assertThat(c.all().sureWrong()).isEqualTo(3);
        assertThat(c.all().sureAccuracy()).isEqualTo(0.75);
        assertThat(c.all().unsureAccuracy()).isEqualTo(0.375);
        assertThat(c.all().enough()).isTrue();
        assertThat(c.earlier().total()).isZero();
        assertThat(c.earlier().illusion()).isNull();      // 분모 0 은 null 그대로
        assertThat(c.earlier().bias()).isNull();
        server.verify();
    }

    @Test
    void readFailureIsThrown() {
        // 답을 넘길 때와 달리, 조회는 보여 줄 값이 없으니 예외를 올린다 (컨트롤러가 503 으로 바꾼다)
        server.expect(requestTo("http://judge/learner/reviews/" + USER)).andRespond(withServerError());

        assertThatThrownBy(() -> client.reviews(USER)).isInstanceOf(RestClientException.class);
        server.verify();
    }
}
