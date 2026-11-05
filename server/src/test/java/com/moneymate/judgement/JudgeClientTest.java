package com.moneymate.judgement;

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
import org.springframework.test.json.JsonCompareMode;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/** JudgeClient 가 FastAPI /judge 와 같은 JSON 모양을 주고받는지 (가짜 서버). */
class JudgeClientTest {

    MockRestServiceServer server;
    JudgeClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://judge");
        server = MockRestServiceServer.bindTo(builder).build();
        client = new JudgeClient(builder.build());
    }

    JudgeApiRequest request() {
        return new JudgeApiRequest("동결 때문에 은행 이익이 는다",
                "[{\"text\":\"3% 동결\",\"keywords\":[\"3%\"]}]",
                "[{\"name\":\"기준금리 동결\",\"aliases\":[\"동결\"]}]",
                "[]", 3L, 7L);
    }

    @Test
    void sendsSnakeCaseWithRawJsonAndParsesResponse() {
        // judge_api.py JudgeRequest 와 같은 이름(snake_case), key_facts·chain·counter 는 문자열이 아니라 JSON 배열
        server.expect(requestTo("http://judge/judge"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().json("""
                        {"answer":"동결 때문에 은행 이익이 는다",
                         "key_facts":[{"text":"3% 동결","keywords":["3%"]}],
                         "chain":[{"name":"기준금리 동결","aliases":["동결"]}],
                         "counter":[], "card_id":3, "step_id":7}""", JsonCompareMode.STRICT))
                .andRespond(withSuccess("""
                        {"rubric":{"evidence":1,"reasoning":3,"rebuttal":0},"total":4,"score":44,
                         "matched_facts":["3% 동결"],"matched_concepts":["기준금리 동결"],
                         "grader":"claude","reasons":{"reasoning":"이었어요","rebuttal":"없어요"},
                         "feedback":{"good":"잘 이었어요","think_more":"다른 힘도 보세요",
                                     "chain":[{"name":"기준금리 동결","used":true},{"name":"은행 실적","used":false}],
                                     "chain_comment":"은행 실적까지 이어 보세요"}}""",
                        MediaType.APPLICATION_JSON));

        JudgeApiResponse r = client.judge(request());

        assertThat(r.rubric()).isEqualTo(new Rubric(1, 3, 0));
        assertThat(r.score()).isEqualTo(44);
        assertThat(r.grader()).isEqualTo("claude");
        assertThat(r.reasons()).containsEntry("rebuttal", "없어요");
        // snake_case(think_more, chain_comment) 를 camelCase 필드로 받는다
        assertThat(r.feedback()).isEqualTo(new JudgementFeedback("잘 이었어요", "다른 힘도 보세요",
                java.util.List.of(new JudgementFeedback.ChainItem("기준금리 동결", true),
                        new JudgementFeedback.ChainItem("은행 실적", false)),
                "은행 실적까지 이어 보세요"));
        server.verify();
    }

    @Test
    void serverErrorThrows() {
        server.expect(requestTo("http://judge/judge")).andRespond(withServerError());
        assertThatThrownBy(() -> client.judge(request())).isInstanceOf(RestClientException.class);
    }

    @Test
    void emptyBodyThrows() {
        server.expect(requestTo("http://judge/judge")).andRespond(withSuccess("{}", MediaType.APPLICATION_JSON));
        assertThatThrownBy(() -> client.judge(request())).isInstanceOf(RestClientException.class);
    }
}
