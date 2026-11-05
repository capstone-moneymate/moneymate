package com.moneymate.judgement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.web.client.ResourceAccessException;

/** JudgementService 테스트. DB(JudgementRepository)와 FastAPI(JudgeClient)는 가짜로 바꾼다. */
class JudgementServiceTest {

    static final UUID USER = UUID.fromString("11111111-2222-3333-4444-555555555555");
    static final JudgementStep STEP = new JudgementStep(7L, 3L,
            "[{\"text\":\"3% 동결\",\"keywords\":[\"3%\"]}]",
            "[{\"name\":\"기준금리 동결\",\"aliases\":[\"동결\"]}]",
            "[]",
            new String[] {"rate_hold"});
    static final String ANSWER = "금리가 동결되어 예대금리차가 유지되니 은행 이익이 버틸 것 같다.";
    // 2026-11-05 01:30 KST (= 11-04 16:30 UTC). 오늘 시작은 2026-11-05 00:00 KST
    static final Clock CLOCK = Clock.fixed(Instant.parse("2026-11-04T16:30:00Z"), ZoneOffset.UTC);

    JudgementRepository repo;
    JudgeClient client;
    JudgementService service;

    @BeforeEach
    void setUp() {
        repo = mock(JudgementRepository.class);
        client = mock(JudgeClient.class);
        service = new JudgementService(repo, client, new JudgeProperties("http://judge", 30, 5), CLOCK);
        when(repo.findStep(7L)).thenReturn(Optional.of(STEP));
        when(repo.findReusable(anyLong(), anyString())).thenReturn(Optional.empty());
    }

    JudgementRequest req(String answer) {
        return new JudgementRequest(USER, 7L, "관망", answer);
    }

    @Test
    void gradesWithClaudeAndSaves() {
        when(client.judge(any())).thenReturn(new JudgeApiResponse(new Rubric(2, 3, 1), 6, 67, "claude",
                Map.of("reasoning", "사슬로 이었어요.", "rebuttal", "위험만 언급했어요.")));

        JudgementResponse r = service.judge(req(ANSWER));

        // 6/9 -> 67 >= 60 이라 맞음
        assertThat(r.score()).isEqualTo(67);
        assertThat(r.correct()).isTrue();
        assertThat(r.grader()).isEqualTo("claude");
        assertThat(r.reused()).isFalse();
        assertThat(r.message()).isNull();
        assertThat(r.reasons()).containsEntry("reasoning", "사슬로 이었어요.");

        ArgumentCaptor<JudgeApiRequest> sent = ArgumentCaptor.forClass(JudgeApiRequest.class);
        verify(client).judge(sent.capture());
        assertThat(sent.getValue().answer()).isEqualTo(ANSWER);
        assertThat(sent.getValue().chain()).isEqualTo(STEP.chainJson());
        assertThat(sent.getValue().cardId()).isEqualTo(3L);

        verify(repo).ensureUser(USER.toString());
        verify(repo).insertAnswer(eq(USER.toString()), eq(3L), eq(7L), eq("관망"), eq(ANSWER),
                eq(AnswerHasher.hash(7L, ANSWER)), eq(true), eq(67), eq(new Rubric(2, 3, 1)), eq("llm"));
    }

    @Test
    void below60IsNotCorrectAndRuleGraderSavedAsRule() {
        when(client.judge(any())).thenReturn(new JudgeApiResponse(new Rubric(1, 2, 2), 5, 56, "rule", Map.of()));

        JudgementResponse r = service.judge(req(ANSWER));

        // 5/9 -> 56 < 60
        assertThat(r.correct()).isFalse();
        assertThat(r.grader()).isEqualTo("rule");
        verify(repo).insertAnswer(anyString(), anyLong(), anyLong(), any(), anyString(), anyString(),
                eq(false), eq(56), any(), eq("rule"));
    }

    @Test
    void reusesSameAnswerWithoutCallingJudge() {
        String hash = AnswerHasher.hash(7L, ANSWER);
        when(repo.findReusable(7L, hash)).thenReturn(Optional.of(new StoredGrade(78, 2, 4, 1, "llm")));

        // 띄어쓰기·줄바꿈만 다른 같은 답안
        JudgementResponse r = service.judge(req("  " + ANSWER.replace(" ", "\n ") + " "));

        assertThat(r.reused()).isTrue();
        assertThat(r.score()).isEqualTo(78);
        assertThat(r.rubric()).isEqualTo(new Rubric(2, 4, 1));
        verify(client, never()).judge(any());
        verify(repo).insertAnswer(anyString(), eq(3L), eq(7L), any(), anyString(), eq(hash),
                eq(true), eq(78), eq(new Rubric(2, 4, 1)), eq("llm"));
    }

    @Test
    void dailyLimitBlocksBeforeJudging() {
        OffsetDateTime startKst = OffsetDateTime.parse("2026-11-05T00:00+09:00");
        when(repo.countJudgementsSince(USER.toString(), startKst)).thenReturn(5);

        assertThatThrownBy(() -> service.judge(req(ANSWER)))
                .isInstanceOf(JudgementExceptions.DailyLimitExceeded.class);
        verify(client, never()).judge(any());
        verify(repo, never()).insertAnswer(any(), anyLong(), anyLong(), any(), any(), any(), any(), any(), any(), any());
    }

    @Test
    void underLimitPasses() {
        when(repo.countJudgementsSince(anyString(), any())).thenReturn(4);
        when(client.judge(any())).thenReturn(new JudgeApiResponse(new Rubric(0, 0, 0), 0, 0, "rule", null));

        JudgementResponse r = service.judge(req(ANSWER));

        assertThat(r.score()).isZero();
        assertThat(r.reasons()).isEmpty();   // reasons 가 null 이어도 빈 객체로
    }

    @Test
    void judgeServerFailureReturnsFixedMessageAndSavesAnswer() {
        when(client.judge(any())).thenThrow(new ResourceAccessException("Connection refused"));

        JudgementResponse r = service.judge(req(ANSWER));

        assertThat(r.score()).isNull();
        assertThat(r.correct()).isNull();
        assertThat(r.rubric()).isNull();
        assertThat(r.grader()).isNull();
        assertThat(r.message()).isEqualTo(JudgementService.FALLBACK_MESSAGE);
        verify(repo).insertAnswer(anyString(), eq(3L), eq(7L), any(), eq(ANSWER), anyString(),
                isNull(), isNull(), isNull(), isNull());
    }

    @Test
    void unknownStepIs404() {
        when(repo.findStep(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.judge(new JudgementRequest(USER, 99L, null, ANSWER)))
                .isInstanceOf(JudgementExceptions.StepNotFound.class);
        verify(client, never()).judge(any());
    }

    @Test
    void startOfTodayIsKstMidnight() {
        assertThat(service.startOfTodayKst()).isEqualTo(OffsetDateTime.parse("2026-11-05T00:00+09:00"));
    }
}
