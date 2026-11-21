package com.moneymate.answer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** AnswerHistoryService 테스트. DB 줄을 화면이 쓰는 답·채점 결과 모양으로 바꾸는지 손으로 확인한다. */
class AnswerHistoryServiceTest {

    static final String USER = "11111111-2222-3333-4444-555555555555";
    static final LocalDate DAY = LocalDate.of(2026, 11, 20);

    final AnswerHistoryRepository repo = mock(AnswerHistoryRepository.class);
    final AnswerHistoryService service = new AnswerHistoryService(repo);

    @Test
    void quizKeepsPickedOptionAndAnswerKey() {
        when(repo.findPastAnswers(USER, 7L, DAY)).thenReturn(List.of(new PastAnswerRow(
                31, "quiz", "{\"kind\": \"quiz\", \"option_index\": 1}", false, null, null, null, "code",
                "{\"correct\": 2, \"explanation\": \"동결은 그대로 둔다는 뜻\"}")));

        PastAnswer p = service.history(USER, 7L, DAY).get(0);

        assertThat(p.stepId()).isEqualTo("31");
        assertThat(p.input()).containsEntry("kind", "quiz").containsEntry("optionIndex", 1);
        assertThat(p.result()).isEqualTo(new PastAnswer.Result("31", false, "동결은 그대로 둔다는 뜻", 2, null));
    }

    @Test
    void causalOrderKeepsOrderAndCorrectPath() {
        when(repo.findPastAnswers(USER, 7L, null)).thenReturn(List.of(new PastAnswerRow(
                32, "causal_order", "{\"kind\": \"causal_order\", \"order\": [\"b\", \"a\"]}", false, null, null,
                null, "code", "{\"correct\": [\"a\", \"b\"]}")));

        PastAnswer p = service.history(USER, 7L, null).get(0);

        assertThat(p.input()).containsEntry("order", List.of("b", "a"));
        assertThat(p.result().correct()).isEqualTo(List.of("a", "b"));
        assertThat(p.result().explanation()).isNull();
    }

    @Test
    void judgementBecomesGradeWithFeedback() {
        when(repo.findPastAnswers(USER, 7L, DAY)).thenReturn(List.of(new PastAnswerRow(
                33, "judgement", "{\"choice\": \"지켜본다\", \"text\": \"금리가 그대로라서\"}", true, 67,
                "{\"evidence\": 2, \"reasoning\": 3, \"rebuttal\": 1}",
                "{\"feedback\": {\"good\": \"좋아요\"}, \"reasons\": {\"reasoning\": \"연결이 맞아요\"}}", "llm",
                null)));

        PastAnswer p = service.history(USER, 7L, DAY).get(0);

        assertThat(p.input()).containsEntry("choice", "지켜본다").containsEntry("reason", "금리가 그대로라서");
        Map<String, Object> g = p.result().grade();
        assertThat(g).containsEntry("score", 67).containsEntry("correct", true)
                .containsEntry("grader", "claude").containsEntry("message", null);
        assertThat(g.get("rubric")).isEqualTo(Map.of("evidence", 2, "reasoning", 3, "rebuttal", 1));
        assertThat(g.get("feedback")).isEqualTo(Map.of("good", "좋아요"));
        assertThat(g.get("reasons")).isEqualTo(Map.of("reasoning", "연결이 맞아요"));
    }

    @Test
    void ungradedJudgementHasMessage() {
        when(repo.findPastAnswers(USER, 7L, DAY)).thenReturn(List.of(new PastAnswerRow(
                33, "judgement", "{\"choice\": \"지켜본다\", \"text\": \"이유\"}", null, null, null, null, null,
                null)));

        Map<String, Object> g = service.history(USER, 7L, DAY).get(0).result().grade();

        assertThat(g).containsEntry("score", null).containsEntry("grader", null)
                .containsEntry("message", "이 답안은 채점하지 못했어요.");
        assertThat(g.get("reasons")).isEqualTo(Map.of());
    }

    @Test
    void noAnswersGivesEmptyList() {
        when(repo.findPastAnswers(USER, 7L, DAY)).thenReturn(List.of());
        assertThat(service.history(USER, 7L, DAY)).isEmpty();
    }
}
