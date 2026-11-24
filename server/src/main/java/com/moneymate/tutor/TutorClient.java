package com.moneymate.tutor;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.moneymate.judgement.JudgeProperties;
import com.moneymate.tutor.TutorDtos.TutorState;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * 튜터 에이전트 요청 (사람1, #240). 튜터는 채점 서버의 /tutor 라우터(worker/tutor/api.py)가 돌리고, 여기서는 넘기기만 한다.
 * 주소는 판단 채점과 같은 서버라 moneymate.judge.url 을 같이 쓴다.
 * 튜터는 한 요청 안에서 모델을 여러 번 부르고 퀴즈도 만든다(출제와 내용 검사). 그래서 오래 기다린다.
 * 실패는 예외로 올린다 (TutorController 가 503 으로, 채점 서버가 4xx 를 주면 그 뜻에 맞는 상태로 바꾼다).
 */
@Component
public class TutorClient {

    /** 시작·답 한 번에 모델 호출 여러 번 + 퀴즈 출제·검사까지라 길게 (2026-11-24 시연에서 한 단계 수 초~십수 초) */
    static final Duration READ_TIMEOUT = Duration.ofSeconds(90);

    private final RestClient restClient;

    @Autowired
    public TutorClient(JudgeProperties props) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(2));
        factory.setReadTimeout(READ_TIMEOUT);
        this.restClient = RestClient.builder().baseUrl(props.url()).requestFactory(factory).build();
    }

    /** 테스트용: 가짜 서버에 묶은 RestClient 를 받는다. */
    TutorClient(RestClient restClient) {
        this.restClient = restClient;
    }

    /** 카드의 개념 단계 튜터를 시작한다 (POST /tutor/start). 없는 카드면 404 */
    public TutorState start(String userId, long cardId) {
        return post("/tutor/start", new StartBody(userId, cardId));
    }

    /**
     * 기다리는 퀴즈의 답을 낸다 (POST /tutor/{sessionId}/answer).
     *
     * @param answer 보기 고르기는 보기 번호(0부터), 칩 빈칸은 빈칸 순서대로 칩 번호, 짝 맞추기는 용어 순서대로 뜻 번호,
     *               사례 분류는 사례 순서대로 바구니 번호
     * @throws RestClientException 없는(또는 남의) 세션이면 404, 기다리는 퀴즈가 없거나 앞의 답을 처리 중이면 409
     */
    public TutorState answer(String sessionId, String userId, Object answer, Integer confidence, Integer responseMs,
                             Integer answerChanges) {
        return post("/tutor/{id}/answer", new AnswerBody(userId, answer, confidence, responseMs, answerChanges), sessionId);
    }

    /** 지금 상태와 지금까지의 이벤트 전부 (GET /tutor/{sessionId}). 화면을 새로 열었을 때 */
    public TutorState get(String sessionId, String userId) {
        TutorState out = restClient.get().uri("/tutor/{id}?user_id={u}", sessionId, userId).retrieve().body(TutorState.class);
        if (out == null) {
            throw new RestClientException("채점 서버 응답이 비어 있어요: /tutor/" + sessionId);
        }
        return out;
    }

    private TutorState post(String path, Object body, Object... vars) {
        TutorState out = restClient.post().uri(path, vars).contentType(MediaType.APPLICATION_JSON).body(body)
                .retrieve().body(TutorState.class);
        if (out == null) {
            throw new RestClientException("채점 서버 응답이 비어 있어요: " + path);
        }
        return out;
    }

    record StartBody(@JsonProperty("user_id") String userId, @JsonProperty("card_id") long cardId) {
    }

    record AnswerBody(
            @JsonProperty("user_id") String userId,
            Object answer,
            Integer confidence,
            @JsonProperty("response_ms") Integer responseMs,
            @JsonProperty("answer_changes") Integer answerChanges) {
    }
}
