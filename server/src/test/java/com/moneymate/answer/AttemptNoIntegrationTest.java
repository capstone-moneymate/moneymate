package com.moneymate.answer;

import static org.assertj.core.api.Assertions.assertThat;

import com.moneymate.TestDatabase;
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
 * 시도 번호 (#215, 계획 1-4). 두 저장 쿼리(AnswerRepository, JudgementRepository)가 attempt_no 를 맞게 넣는지
 * 빈 PostgreSQL 16 에 db/migrations 와 fixtures/attempts.sql 을 넣고 확인한다. Docker 가 없으면 건너뛴다.
 * 규칙: 카드의 첫 답 단계(개념 단계 제외)를 다시 풀면 새 시도, 그 밖의 단계는 지금 시도 그대로.
 */
@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class AttemptNoIntegrationTest {

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
    JdbcTemplate jdbc;

    @BeforeEach
    void clean() {
        jdbc.update("DELETE FROM user_answers");
        answers.ensureUser(ME);
        answers.ensureUser(YOU);
    }

    void quiz(String user, long card, long step) {
        answers.insertAnswer(user, card, step, "{\"kind\":\"quiz\",\"option_index\":0}", true, null, null, null);
    }

    void judge(String user, long step) {
        judgements.insertAnswer(user, 1L, step, "A", "글", "hash-" + UUID.randomUUID(), true, 70,
                new Rubric(2, 3, 1), "llm", "피드백");
    }

    /** 저장 순서대로 (단계, 시도 번호) */
    List<String> attempts(String user, long card) {
        return jdbc.queryForList("SELECT step_id || ':' || attempt_no FROM user_answers"
                + " WHERE user_id = CAST(? AS uuid) AND card_id = ? ORDER BY id", String.class, user, card);
    }

    @Test
    void firstPlayIsAttemptOne() {
        quiz(ME, 1, 102);
        quiz(ME, 1, 103);
        judge(ME, 104);
        assertThat(attempts(ME, 1)).containsExactly("102:1", "103:1", "104:1");
    }

    @Test
    void replayingFromFirstAnswerStepStartsNewAttempt() {
        quiz(ME, 1, 102);
        quiz(ME, 1, 103);
        judge(ME, 104);
        quiz(ME, 1, 102);   // 다시 풀기: 첫 답 단계(102, 개념 단계 101 은 빼고 첫 번째)
        quiz(ME, 1, 103);
        judge(ME, 104);
        quiz(ME, 1, 102);   // 세 번째
        assertThat(attempts(ME, 1)).containsExactly("102:1", "103:1", "104:1", "102:2", "103:2", "104:2", "102:3");
    }

    @Test
    void resubmittingLaterStepStaysInSameAttempt() {
        quiz(ME, 1, 102);
        judge(ME, 104);
        judge(ME, 104);     // 판단해보기를 고쳐서 다시 냄 → 같은 시도
        quiz(ME, 1, 103);   // 순서가 바뀌어도 첫 단계가 아니면 같은 시도
        assertThat(attempts(ME, 1)).containsExactly("102:1", "104:1", "104:1", "103:1");
    }

    @Test
    void startingFromLaterStepIsStillAttemptOne() {
        quiz(ME, 1, 103);   // 기록이 없으면 어느 단계든 1
        quiz(ME, 1, 102);   // 그다음 첫 단계를 내면 이미 시도 1이 있으니 2
        assertThat(attempts(ME, 1)).containsExactly("103:1", "102:2");
    }

    @Test
    void usersAndCardsAreCountedSeparately() {
        quiz(ME, 1, 102);
        quiz(ME, 1, 102);   // 나: 카드 1 시도 2
        quiz(YOU, 1, 102);  // 다른 사용자는 1부터
        quiz(ME, 2, 201);   // 다른 카드도 1부터
        quiz(ME, 2, 202);
        assertThat(attempts(ME, 1)).containsExactly("102:1", "102:2");
        assertThat(attempts(YOU, 1)).containsExactly("102:1");
        assertThat(attempts(ME, 2)).containsExactly("201:1", "202:1");
    }
}
