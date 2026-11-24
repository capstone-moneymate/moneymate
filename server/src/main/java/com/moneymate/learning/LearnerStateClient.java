package com.moneymate.learning;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.moneymate.judgement.JudgeProperties;
import com.moneymate.learning.LearnerDtos.Calibration;
import com.moneymate.learning.LearnerDtos.ReviewQueue;
import com.moneymate.learning.LearnerDtos.ReviewQuiz;
import com.moneymate.learning.LearnerDtos.ReviewResult;
import java.time.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/**
 * 학습자 상태(BKT 알 확률, FSRS 복습 일정) 갱신 요청 (사람2, docs/추가구현_계획.md 2-3·2-4).
 * 계산과 저장은 채점 서버의 POST /learner/answer (worker/learner/api.py)가 한다. 여기서는 채점 결과를 넘기기만 한다.
 * 주소는 판단 채점과 같은 서버라 moneymate.judge.url 을 같이 쓴다.
 *
 * 답을 넘기는 recordAnswer 는 실패해도 예외를 올리지 않는다. 알 확률을 못 고쳤다고 채점 응답이 깨지면 안 되기 때문이다 (로그만 남긴다).
 * 조회(reviews, calibration)와 복습 문제(reviewQuiz, reviewAnswer)는 보여 줄 값이 없으니 예외를 그대로 올린다
 * (LearnerController 가 503 으로, 채점 서버가 4xx 를 주면 그 뜻에 맞는 상태로 바꾼다).
 */
@Component
public class LearnerStateClient {

    private static final Logger log = LoggerFactory.getLogger(LearnerStateClient.class);

    /** 복습 문제 만들기는 채점 서버가 LLM 을 불러서(모양이 틀리면 한 번 더) 오래 걸릴 수 있다 */
    static final Duration QUIZ_READ_TIMEOUT = Duration.ofSeconds(30);

    private final RestClient restClient;
    private final RestClient quizClient;

    @Autowired
    public LearnerStateClient(JudgeProperties props) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        // LLM 을 부르지 않는 짧은 요청이라 판단 채점(30초)보다 훨씬 짧게 기다린다
        factory.setConnectTimeout(Duration.ofSeconds(2));
        factory.setReadTimeout(Duration.ofSeconds(3));
        this.restClient = RestClient.builder().baseUrl(props.url()).requestFactory(factory).build();
        SimpleClientHttpRequestFactory slow = new SimpleClientHttpRequestFactory();
        slow.setConnectTimeout(Duration.ofSeconds(2));
        slow.setReadTimeout(QUIZ_READ_TIMEOUT);
        this.quizClient = RestClient.builder().baseUrl(props.url()).requestFactory(slow).build();
    }

    /** 테스트용: 가짜 서버에 묶은 RestClient 를 받는다. */
    LearnerStateClient(RestClient restClient) {
        this.restClient = restClient;
        this.quizClient = restClient;
    }

    /**
     * 본 문제 답 하나를 그 단계의 개념마다 알 확률과 복습 일정에 반영한다.
     *
     * @param conceptIds 그 단계의 인과 사전 개념 id (steps.content.concept_ids). 비어 있으면 부르지 않는다
     * @param kind       quiz / chart / causal_order
     * @param count      찍어서 맞힐 확률 계산용: quiz·chart 는 보기 수, causal_order 는 놓을 개념 수
     * @param confidence    1 헷갈려요, 2 확실해요. 복습 일정의 자동 평가에 쓴다. 없으면 null
     * @param responseMs    응답 시간(ms). 없으면 null
     * @param answerChanges 답을 바꾼 횟수. 없으면 null
     * @return 반영했으면 true. 개념이 없거나 채점 서버가 실패하면 false
     */
    public boolean recordAnswer(String userId, String[] conceptIds, boolean correct, String kind, int count,
                                Integer confidence, Integer responseMs, Integer answerChanges) {
        if (conceptIds == null || conceptIds.length == 0 || count < 1) {
            return false;
        }
        try {
            restClient.post()
                    .uri("/learner/answer")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(new Body(userId, conceptIds, correct, kind, count, confidence, responseMs, answerChanges))
                    .retrieve()
                    .toBodilessEntity();
            return true;
        } catch (RestClientException e) {
            log.warn("알 확률을 고치지 못했어요 (userId={}, kind={}): {}", userId, kind, e.getMessage());
            return false;
        }
    }

    /**
     * 오늘 복습할 개념 (GET /learner/reviews/{user_id}).
     *
     * @throws RestClientException 연결 실패·시간 초과·4xx·5xx·응답이 비어 있음
     */
    public ReviewQueue reviews(String userId) {
        return get("/learner/reviews/{userId}", userId, ReviewQueue.class);
    }

    /**
     * 확신 보정 2 × 2 표와 지표 (GET /learner/calibration/{user_id}).
     *
     * @throws RestClientException 연결 실패·시간 초과·4xx·5xx·응답이 비어 있음
     */
    public Calibration calibration(String userId) {
        return get("/learner/calibration/{userId}", userId, Calibration.class);
    }

    /**
     * 오늘 복습할 개념의 문제 하나 (POST /learner/review/quiz). 안 푼 문제가 있으면 그 문제가 다시 온다.
     *
     * @throws RestClientException 연결 실패·시간 초과·응답이 비어 있음. 오늘 복습할 개념이 아니면 409, 문제를 못 만들면 503
     */
    public ReviewQuiz reviewQuiz(String userId, long nodeId) {
        return post(quizClient, "/learner/review/quiz", new QuizBody(userId, nodeId), ReviewQuiz.class);
    }

    /**
     * 복습 문제의 답을 채점하고 알 확률·복습 일정에 반영한다 (POST /learner/review/answer).
     *
     * @param answer 고른 보기 번호 (0부터)
     * @throws RestClientException 연결 실패·시간 초과·응답이 비어 있음. 없는 문제면 404, 이미 답했으면 409
     */
    public ReviewResult reviewAnswer(String userId, long quizId, Object answer, Integer confidence,
                                     Integer responseMs, Integer answerChanges) {
        return post(restClient, "/learner/review/answer",
                new ReviewAnswerBody(userId, quizId, answer, confidence, responseMs, answerChanges), ReviewResult.class);
    }

    private <T> T post(RestClient client, String path, Object body, Class<T> type) {
        T out = client.post().uri(path).contentType(MediaType.APPLICATION_JSON).body(body).retrieve().body(type);
        if (out == null) {
            throw new RestClientException("채점 서버 응답이 비어 있어요: " + path);
        }
        return out;
    }

    private <T> T get(String path, String userId, Class<T> type) {
        T body = restClient.get().uri(path, userId).retrieve().body(type);
        if (body == null) {
            throw new RestClientException("채점 서버 응답이 비어 있어요: " + path);
        }
        return body;
    }

    /** worker/learner/api.py 의 ReviewQuizIn. */
    record QuizBody(@JsonProperty("user_id") String userId, @JsonProperty("node_id") long nodeId) {
    }

    /** worker/learner/api.py 의 ReviewAnswerIn. */
    record ReviewAnswerBody(
            @JsonProperty("user_id") String userId,
            @JsonProperty("quiz_id") long quizId,
            Object answer,
            Integer confidence,
            @JsonProperty("response_ms") Integer responseMs,
            @JsonProperty("answer_changes") Integer answerChanges) {
    }

    /** worker/learner/api.py 의 AnswerIn. */
    record Body(
            @JsonProperty("user_id") String userId,
            @JsonProperty("concept_ids") String[] conceptIds,
            boolean correct,
            String kind,
            int count,
            Integer confidence,
            @JsonProperty("response_ms") Integer responseMs,
            @JsonProperty("answer_changes") Integer answerChanges) {
    }
}
