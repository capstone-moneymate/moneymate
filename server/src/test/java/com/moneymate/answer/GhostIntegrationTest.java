package com.moneymate.answer;

import static org.assertj.core.api.Assertions.assertThat;

import com.moneymate.TestDatabase;
import com.moneymate.answer.GhostDtos.Cell;
import com.moneymate.answer.GhostDtos.Report;
import com.moneymate.answer.GhostRepository.GhostStep;
import com.moneymate.judgement.JudgementRepository;
import com.moneymate.judgement.Rubric;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.jdbc.core.JdbcTemplate;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

/**
 * 고스트 비교 읽기 SQL (계획 2-6). 실제 저장 쿼리(시도 번호 #215 포함)로 답안을 넣고 GhostRepository 가
 * (시도, 단계)마다 마지막 답안을 읽는지, 그 결과로 비교가 나오는지 확인한다. Docker 가 없으면 건너뛴다.
 * fixtures/attempts.sql: 카드 1 = 개념(101) → 퀴즈(102) → 차트(103) → 판단(104).
 */
@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class GhostIntegrationTest {

    @Container
    @ServiceConnection
    static final PostgreSQLContainer POSTGRES = TestDatabase.postgres("fixtures/attempts.sql");

    static final String ME = "11111111-2222-3333-4444-555555555555";
    static final String YOU = "99999999-8888-7777-6666-555555555555";

    @Autowired
    AnswerRepository answers;
    @Autowired
    JudgementRepository judgements;
    @Autowired
    GhostRepository ghosts;
    @Autowired
    JdbcTemplate jdbc;

    @BeforeEach
    void clean() {
        jdbc.update("DELETE FROM user_answers");
        answers.ensureUser(ME);
        answers.ensureUser(YOU);
    }

    void quiz(String user, long step, boolean correct, Integer confidence, Integer ms) {
        answers.insertAnswer(user, 1L, step, "{\"kind\":\"quiz\",\"option_index\":0}", correct, confidence, ms, 0);
    }

    void judge(String user, int score) {
        judgements.insertAnswer(user, 1L, 104L, "A", "글", "hash-" + UUID.randomUUID(), score >= 60, score,
                new Rubric(2, 3, 1), "llm", "피드백");
    }

    Report report(String user) {
        return Ghost.report(ghosts.findSteps(1L), ghosts.findRows(user, 1L));
    }

    @Test
    void answerStepsSkipConceptStep() {
        assertThat(ghosts.findSteps(1L)).containsExactly(new GhostStep(102, "quiz"), new GhostStep(103, "chart"),
                new GhostStep(104, "judgement"));
    }

    @Test
    void comparesLatestAttemptWithPreviousCompleteOne() {
        quiz(ME, 102, false, 2, 12_000);
        quiz(ME, 103, true, 1, 25_000);
        judge(ME, 52);
        judge(ME, 55);                      // 같은 시도에서 고쳐서 다시 냄 → 마지막 점수 55 가 그 시도 기록
        quiz(ME, 102, true, 2, 5_000);      // 첫 답 단계를 다시 냄 → 시도 2
        quiz(ME, 103, true, 2, 25_000);
        judge(ME, 71);
        quiz(YOU, 102, true, 2, 1_000);     // 다른 사용자 기록은 섞이지 않는다

        Report r = report(ME);

        assertThat(ghosts.findRows(ME, 1L)).hasSize(6);
        assertThat(r.lastComplete().attemptNo()).isEqualTo(2);
        assertThat(r.comparison().previous().attemptNo()).isEqualTo(1);
        assertThat(r.comparison().previous().date()).isNotNull();
        assertThat(r.comparison().rows()).extracting(GhostDtos.Row::stepId).containsExactly("102", "103", "104");
        assertThat(r.comparison().rows().get(0).previous()).isEqualTo(new Cell(false, 12, null));
        assertThat(r.comparison().rows().get(0).current()).isEqualTo(new Cell(true, 5, null));
        assertThat(r.comparison().rows().get(2).previous()).isEqualTo(new Cell(false, null, 55));
        assertThat(r.comparison().rows().get(2).current()).isEqualTo(new Cell(true, null, 71));
        assertThat(r.comparison().rows()).extracting(GhostDtos.Row::improved).containsExactly(true, false, true);
        assertThat(r.comparison().improvedSteps()).isEqualTo(2);
        assertThat(r.comparison().previous().sureWrong()).isEqualTo(1);
        assertThat(r.comparison().current().sureWrong()).isEqualTo(0);
    }

    @Test
    void firstTimeHasNoComparison() {
        quiz(ME, 102, true, 2, 5_000);

        Report r = report(ME);

        assertThat(r.lastComplete()).isNull();   // 아직 끝까지 풀지 않았다
        assertThat(r.comparison()).isNull();
        assertThat(report(YOU)).isEqualTo(new Report(null, null));
    }
}
