package com.moneymate.answer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

/** AnswerService 테스트. DB(AnswerRepository)는 가짜로 바꾼다. */
class AnswerServiceTest {

    static final UUID USER = UUID.fromString("11111111-2222-3333-4444-555555555555");
    static final AnswerStep QUIZ = new AnswerStep(10L, 3L, "quiz",
            "{\"correct\": 2, \"explanation\": \"동결은 금리를 그대로 두는 것이에요.\"}", 4, new String[] {"rate_hold"});
    static final AnswerStep CHART = new AnswerStep(11L, 3L, "chart",
            "{\"correct\": 0, \"explanation\": \"거래량이 늘었어요.\", \"check\": {\"metric\": \"volume\"}}", 3,
            new String[] {"volume"});
    static final AnswerStep ORDER = new AnswerStep(12L, 3L, "causal_order",
            "{\"correct\": [\"rate_hold\", \"loan_spread\", \"bank_profit\"], \"explanation\": \"동결 → 예대금리차 → 은행 실적\","
                    + " \"change\": \"up\", \"direction\": \"same\", \"evidence_quote\": \"3.00%\"}",
            0, new String[] {"rate_hold", "loan_spread", "bank_profit"});
    static final AnswerStep JUDGE = new AnswerStep(13L, 3L, "judgement", "{\"chain\": [], \"counter\": []}", 0,
            new String[] {});

    AnswerRepository repo;
    AnswerService service;

    @BeforeEach
    void setUp() {
        repo = mock(AnswerRepository.class);
        service = new AnswerService(repo, false);
        for (AnswerStep s : List.of(QUIZ, CHART, ORDER, JUDGE)) {
            when(repo.findStep(s.stepId(), false)).thenReturn(Optional.of(s));
        }
    }

    static AnswerRequest pick(long stepId, String kind, Integer index) {
        return new AnswerRequest(USER, stepId, new AnswerRequest.Input(kind, index, null));
    }

    static AnswerRequest order(long stepId, List<String> order) {
        return new AnswerRequest(USER, stepId, new AnswerRequest.Input("causal_order", null, order));
    }

    // --- 퀴즈·차트 ---

    @Test
    void quizCorrectIsSavedAsCode() {
        AnswerResult r = service.submit(pick(10L, "quiz", 2));

        assertThat(r.stepId()).isEqualTo("10");
        assertThat(r.isCorrect()).isTrue();
        assertThat(r.correct()).isEqualTo(2);
        assertThat(r.explanation()).isEqualTo("동결은 금리를 그대로 두는 것이에요.");
        verify(repo).ensureUser(USER.toString());
        verify(repo).insertAnswer(USER.toString(), 3L, 10L, "{\"kind\":\"quiz\",\"option_index\":2}", true);
    }

    @Test
    void quizWrongShowsCorrectIndex() {
        AnswerResult r = service.submit(pick(10L, "quiz", 1));

        assertThat(r.isCorrect()).isFalse();
        assertThat(r.correct()).isEqualTo(2);   // 틀렸을 때 화면이 정답 보기를 보여 준다
        verify(repo).insertAnswer(USER.toString(), 3L, 10L, "{\"kind\":\"quiz\",\"option_index\":1}", false);
    }

    @Test
    void chartIsGradedLikeQuiz() {
        AnswerResult r = service.submit(pick(11L, "chart", 0));

        assertThat(r.isCorrect()).isTrue();
        assertThat(r.explanation()).isEqualTo("거래량이 늘었어요.");
    }

    @Test
    void optionIndexOutOfRangeIs400AndNotSaved() {
        assertThatThrownBy(() -> service.submit(pick(10L, "quiz", 4)))   // 보기 4개 → 0~3
                .isInstanceOf(AnswerExceptions.BadAnswer.class);
        assertThatThrownBy(() -> service.submit(pick(10L, "quiz", -1)))
                .isInstanceOf(AnswerExceptions.BadAnswer.class);
        assertThatThrownBy(() -> service.submit(pick(10L, "quiz", null)))
                .isInstanceOf(AnswerExceptions.BadAnswer.class);
        verify(repo, never()).insertAnswer(anyString(), anyLong(), anyLong(), anyString(), anyBoolean());
    }

    // --- 인과 순서 ---

    @Test
    void causalOrderExactMatchIsCorrect() {
        AnswerResult r = service.submit(order(12L, List.of("rate_hold", "loan_spread", "bank_profit")));

        assertThat(r.isCorrect()).isTrue();
        assertThat(r.correct()).isEqualTo(List.of("rate_hold", "loan_spread", "bank_profit"));
        verify(repo).insertAnswer(eq(USER.toString()), eq(3L), eq(12L),
                eq("{\"kind\":\"causal_order\",\"order\":[\"rate_hold\",\"loan_spread\",\"bank_profit\"]}"), eq(true));
    }

    @Test
    void causalOrderSwappedIsWrong() {
        AnswerResult r = service.submit(order(12L, List.of("loan_spread", "rate_hold", "bank_profit")));

        assertThat(r.isCorrect()).isFalse();
        assertThat(r.explanation()).isEqualTo("동결 → 예대금리차 → 은행 실적");
    }

    @Test
    void causalOrderWithMissingDuplicateOrOtherConceptIs400() {
        for (List<String> bad : List.of(
                List.of("rate_hold", "loan_spread"),                              // 빠뜨림
                List.of("rate_hold", "rate_hold", "bank_profit"),                 // 중복
                List.of("rate_hold", "loan_spread", "exchange_rate"))) {          // 다른 개념
            assertThatThrownBy(() -> service.submit(order(12L, bad)))
                    .isInstanceOf(AnswerExceptions.BadAnswer.class);
        }
        assertThatThrownBy(() -> service.submit(order(12L, null))).isInstanceOf(AnswerExceptions.BadAnswer.class);
        verify(repo, never()).insertAnswer(anyString(), anyLong(), anyLong(), anyString(), anyBoolean());
    }

    // --- 단계 확인 ---

    @Test
    void judgementGoesToJudgementApi() {
        assertThatThrownBy(() -> service.submit(pick(13L, "judgement", 0)))
                .isInstanceOf(AnswerExceptions.BadAnswer.class)
                .hasMessageContaining("/api/judgement");
    }

    @Test
    void kindMismatchIs400() {
        assertThatThrownBy(() -> service.submit(pick(12L, "quiz", 0)))
                .isInstanceOf(AnswerExceptions.BadAnswer.class);
    }

    @Test
    void missingOrHiddenStepIs404() {
        when(repo.findStep(99L, false)).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.submit(pick(99L, "quiz", 0)))
                .isInstanceOf(AnswerExceptions.StepNotFound.class);
        verify(repo, never()).ensureUser(anyString());
    }

    @Test
    void includePendingIsPassedToRepository() {
        AnswerService pending = new AnswerService(repo, true);
        when(repo.findStep(10L, true)).thenReturn(Optional.of(QUIZ));

        assertThat(pending.submit(pick(10L, "quiz", 2)).isCorrect()).isTrue();
    }

    @Test
    void brokenAnswerKeyIs500AndNotSaved() {
        when(repo.findStep(20L, false)).thenReturn(Optional.of(
                new AnswerStep(20L, 3L, "quiz", null, 4, new String[] {})));
        when(repo.findStep(21L, false)).thenReturn(Optional.of(
                new AnswerStep(21L, 3L, "quiz", "{\"correct\": \"둘째\"}", 4, new String[] {})));
        when(repo.findStep(22L, false)).thenReturn(Optional.of(
                new AnswerStep(22L, 3L, "causal_order", "{\"correct\": 1}", 0, new String[] {})));

        assertThatThrownBy(() -> service.submit(pick(20L, "quiz", 0)))
                .isInstanceOf(AnswerExceptions.AnswerKeyMissing.class);
        assertThatThrownBy(() -> service.submit(pick(21L, "quiz", 0)))
                .isInstanceOf(AnswerExceptions.AnswerKeyMissing.class);
        assertThatThrownBy(() -> service.submit(order(22L, List.of("a"))))
                .isInstanceOf(AnswerExceptions.AnswerKeyMissing.class);
        verify(repo, never()).insertAnswer(anyString(), anyLong(), anyLong(), anyString(), anyBoolean());
    }

    // --- JSON 모양 (web 타입) ---

    @Test
    void jsonUsesWebFieldNames() {
        JsonMapper json = JsonMapper.builder().build();
        String out = json.writeValueAsString(new AnswerResult("10", true, "해설", 2));
        assertThat(out).isEqualTo("{\"stepId\":\"10\",\"isCorrect\":true,\"explanation\":\"해설\",\"correct\":2}");

        // web 은 stepId 를 문자열로 보낸다
        AnswerRequest req = json.readValue("""
                {"userId":"11111111-2222-3333-4444-555555555555","stepId":"12",
                 "answer":{"kind":"causal_order","order":["a","b"]}}""", AnswerRequest.class);
        assertThat(req.stepId()).isEqualTo(12L);
        assertThat(req.answer().order()).containsExactly("a", "b");
    }
}
