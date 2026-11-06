package com.moneymate.judgement;

import java.time.Duration;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/** FastAPI 채점 서버(worker/judge_api.py)를 HTTP 로 부른다. LLM 은 여기서 직접 부르지 않는다. */
@Component
public class JudgeClient {

    private final RestClient restClient;

    @Autowired
    public JudgeClient(JudgeProperties props) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(3));
        factory.setReadTimeout(Duration.ofSeconds(props.timeoutSeconds()));
        this.restClient = RestClient.builder().baseUrl(props.url()).requestFactory(factory).build();
    }

    /** 테스트용: 가짜 서버에 묶은 RestClient 를 받는다. */
    JudgeClient(RestClient restClient) {
        this.restClient = restClient;
    }

    /**
     * 답안 1개를 채점한다.
     *
     * @throws RestClientException 연결 실패·시간 초과·4xx·5xx·응답 형식 오류
     */
    public JudgeApiResponse judge(JudgeApiRequest request) {
        JudgeApiResponse body = restClient.post()
                .uri("/judge")
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(JudgeApiResponse.class);
        if (body == null || body.rubric() == null) {
            throw new RestClientException("채점 서버 응답이 비어 있어요");
        }
        return body;
    }
}
