package com.moneymate.answer;

import static org.assertj.core.api.Assertions.assertThat;

import com.moneymate.answer.GhostDtos.Cell;
import com.moneymate.answer.GhostDtos.Comparison;
import com.moneymate.answer.GhostDtos.Report;
import com.moneymate.answer.GhostDtos.Row;
import com.moneymate.answer.GhostRepository.GhostStep;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** 고스트 비교 계산 (계획 2-6). 손으로 만든 답안 기록으로 "지난번 / 이번 / 좋아졌다 / 최고 기록"을 확인한다. */
class GhostTest {

    static final long QUIZ = 102, CHART = 103, ORDER = 104, JUDGE = 105;
    static final List<GhostStep> STEPS = List.of(new GhostStep(QUIZ, "quiz"), new GhostStep(CHART, "chart"),
            new GhostStep(ORDER, "causal_order"), new GhostStep(JUDGE, "judgement"));
    static final LocalDate NOV20 = LocalDate.of(2026, 11, 20), NOV24 = LocalDate.of(2026, 11, 24);

    final List<GhostRow> rows = new ArrayList<>();

    /** 코드 채점 단계 답안 */
    void coded(int attempt, long step, boolean correct, Integer confidence, Integer ms, LocalDate day) {
        rows.add(new GhostRow(attempt, step, correct, null, confidence, ms, day));
    }

    void judged(int attempt, Integer score, LocalDate day) {
        rows.add(new GhostRow(attempt, JUDGE, score == null ? null : score >= 60, score, null, null, day));
    }

    /** 한 시도를 끝까지: 퀴즈·차트·인과 순서(맞음 여부, 초)와 판단 점수 */
    void full(int attempt, LocalDate day, boolean q, int qs, boolean c, int cs, boolean o, int os, int score) {
        coded(attempt, QUIZ, q, 2, qs * 1000, day);
        coded(attempt, CHART, c, 1, cs * 1000, day);
        coded(attempt, ORDER, o, 2, os * 1000, day);
        judged(attempt, score, day);
    }

    Row row(Comparison c, long step) {
        return c.rows().stream().filter(r -> r.stepId().equals(String.valueOf(step))).findFirst().orElseThrow();
    }

    @Test
    void neverSolvedHasNoGhost() {
        assertThat(Ghost.report(STEPS, List.of())).isEqualTo(new Report(null, null));
    }

    @Test
    void firstCompleteAttemptBecomesGhostButHasNothingToCompare() {
        full(1, NOV20, true, 12, true, 25, false, 40, 52);

        Report r = Ghost.report(STEPS, rows);

        assertThat(r.comparison()).isNull();
        assertThat(r.lastComplete().attemptNo()).isEqualTo(1);
        assertThat(r.lastComplete().date()).isEqualTo("2026-11-20");
        assertThat(r.lastComplete().steps()).extracting(s -> s.record().isCorrect())
                .containsExactly(true, true, false, false);   // 판단 52점은 60점 미만
        assertThat(r.lastComplete().steps().get(3).record()).isEqualTo(new Cell(false, null, 52));
    }

    /** 계획 2-6 의 결과 화면 예시: 퀴즈 12초 → 5초, 차트 25초 → 22초, 인과 순서 틀림 → 맞힘, 판단 52 → 71 */
    @Test
    void planExampleImprovesFourSteps() {
        full(1, NOV20, true, 12, true, 25, false, 40, 52);
        full(2, NOV24, true, 5, true, 22, true, 18, 71);

        Comparison c = Ghost.report(STEPS, rows).comparison();

        assertThat(c.previous().attemptNo()).isEqualTo(1);
        assertThat(c.previous().date()).isEqualTo("2026-11-20");
        assertThat(c.current().attemptNo()).isEqualTo(2);
        assertThat(row(c, QUIZ).previous()).isEqualTo(new Cell(true, 12, null));
        assertThat(row(c, QUIZ).current()).isEqualTo(new Cell(true, 5, null));
        assertThat(row(c, JUDGE).previous()).isEqualTo(new Cell(false, null, 52));
        assertThat(row(c, JUDGE).current()).isEqualTo(new Cell(true, null, 71));
        assertThat(c.rows()).extracting(Row::improved).containsExactly(true, true, true, true);
        assertThat(c.improvedSteps()).isEqualTo(4);
        // 지난번: 인과 순서를 "확실해요"(2)라고 하고 틀림 1개 → 이번 0개
        assertThat(c.previous().sureWrong()).isEqualTo(1);
        assertThat(c.current().sureWrong()).isEqualTo(0);
        // 이전 기록이 1번뿐이라 최고 기록은 따지지 않는다
        assertThat(c.rows()).extracting(Row::best).containsOnly(false);
    }

    @Test
    void correctnessComesBeforeTime() {
        full(1, NOV20, true, 12, false, 30, true, 20, 70);
        // 퀴즈: 맞힘 → 틀림(더 빨라도 좋아진 게 아니다), 차트: 틀림 → 틀림(빨라짐), 인과 순서: 맞힘 → 맞힘(느려짐), 판단: 점수 내려감
        full(2, NOV24, false, 3, false, 10, true, 25, 60);

        Comparison c = Ghost.report(STEPS, rows).comparison();

        assertThat(c.rows()).extracting(Row::improved).containsOnly(false);
        assertThat(c.improvedSteps()).isZero();
    }

    @Test
    void timeIsComparedInShownSeconds() {
        // 12.4초와 11.6초는 둘 다 12초로 보인다 → 줄었다고 하지 않는다. 12.4초 → 11.4초는 12 → 11
        coded(1, QUIZ, true, 2, 12_400, NOV20);
        coded(1, CHART, true, 2, 12_400, NOV20);
        coded(1, ORDER, true, 2, 12_400, NOV20);
        judged(1, 70, NOV20);
        coded(2, QUIZ, true, 2, 11_600, NOV24);
        coded(2, CHART, true, 2, 11_400, NOV24);
        coded(2, ORDER, true, 2, null, NOV24);     // 시간 기록이 없으면 비교하지 않는다
        judged(2, 70, NOV24);

        Comparison c = Ghost.report(STEPS, rows).comparison();

        assertThat(row(c, QUIZ).improved()).isFalse();
        assertThat(row(c, CHART).improved()).isTrue();
        assertThat(row(c, ORDER).improved()).isFalse();
        assertThat(row(c, ORDER).current()).isEqualTo(new Cell(true, null, null));
        assertThat(row(c, JUDGE).improved()).isFalse();   // 같은 점수
    }

    @Test
    void secondsRoundAndNeverShowZero() {
        assertThat(Ghost.seconds(400)).isEqualTo(1);
        assertThat(Ghost.seconds(1_499)).isEqualTo(1);
        assertThat(Ghost.seconds(1_500)).isEqualTo(2);
        assertThat(Ghost.seconds(null)).isNull();
    }

    @Test
    void bestRecordNeedsTwoEarlierRecords() {
        full(1, NOV20, true, 12, false, 30, true, 20, 52);
        full(2, NOV20, true, 9, false, 28, true, 15, 71);
        // 퀴즈 8초 < 이전 최고 9초, 차트는 처음 맞힘, 인과 순서 18초는 지난번 15초보다 느림, 판단 80 > 이전 최고 71
        full(3, NOV24, true, 8, true, 27, true, 18, 80);

        Comparison c = Ghost.report(STEPS, rows).comparison();

        assertThat(c.previous().attemptNo()).isEqualTo(2);
        assertThat(c.rows()).extracting(Row::best).containsExactly(true, true, false, true);
        assertThat(c.rows()).extracting(Row::improved).containsExactly(true, true, false, true);
    }

    @Test
    void beatingLastTimeIsNotAlwaysBest() {
        full(1, NOV20, true, 5, true, 10, true, 10, 90);
        full(2, NOV20, true, 9, true, 10, true, 10, 60);
        full(3, NOV24, true, 7, true, 10, true, 10, 75);   // 지난번(9초, 60점)보다는 좋지만 최고(5초, 90점)는 아니다

        Comparison c = Ghost.report(STEPS, rows).comparison();

        assertThat(row(c, QUIZ).improved()).isTrue();
        assertThat(row(c, QUIZ).best()).isFalse();
        assertThat(row(c, JUDGE).improved()).isTrue();
        assertThat(row(c, JUDGE).best()).isFalse();
    }

    @Test
    void unfinishedAttemptIsNotUsedAsGhost() {
        full(1, NOV20, true, 12, true, 25, true, 40, 52);
        coded(2, QUIZ, true, 2, 9_000, NOV20);              // 1번만 풀고 나감
        coded(3, QUIZ, true, 2, 5_000, NOV24);              // 지금 푸는 중 (첫 단계만 냄)

        Report r = Ghost.report(STEPS, rows);

        assertThat(r.lastComplete().attemptNo()).isEqualTo(1);
        assertThat(r.comparison().previous().attemptNo()).isEqualTo(1);
        assertThat(r.comparison().current().attemptNo()).isEqualTo(3);
        assertThat(row(r.comparison(), QUIZ).improved()).isTrue();            // 12초 → 5초
        assertThat(row(r.comparison(), CHART).current()).isNull();            // 아직 안 냄
        assertThat(row(r.comparison(), CHART).improved()).isFalse();
        // 최고 기록: 퀴즈는 이전 기록이 2번(12초, 9초) 있고 5초가 더 빠르다
        assertThat(row(r.comparison(), QUIZ).best()).isTrue();
    }

    @Test
    void lastCompleteIsTheNewestFinishedAttempt() {
        full(1, NOV20, true, 12, true, 25, true, 40, 52);
        full(2, NOV24, true, 5, true, 22, true, 18, 71);

        Report r = Ghost.report(STEPS, rows);

        // 세 번째로 풀러 들어오면 두 번째 시도가 "지난번"이 된다
        assertThat(r.lastComplete().attemptNo()).isEqualTo(2);
        assertThat(r.lastComplete().date()).isEqualTo("2026-11-24");
    }

    @Test
    void sureWrongIsNullWithoutConfidenceRecords() {
        // 확신 버튼(#207) 이전 답안: confidence 가 모두 null
        coded(1, QUIZ, false, null, null, NOV20);
        coded(1, CHART, true, null, null, NOV20);
        coded(1, ORDER, true, null, null, NOV20);
        judged(1, 70, NOV20);
        full(2, NOV24, false, 5, true, 22, true, 18, 71);  // 퀴즈를 "확실해요"라고 하고 틀림

        Comparison c = Ghost.report(STEPS, rows).comparison();

        assertThat(c.previous().sureWrong()).isNull();
        assertThat(c.current().sureWrong()).isEqualTo(1);
        assertThat(row(c, QUIZ).previous()).isEqualTo(new Cell(false, null, null));
    }

    @Test
    void ungradedJudgementIsNotCompared() {
        full(1, NOV20, true, 12, true, 25, true, 40, 52);
        coded(2, QUIZ, true, 2, 12_000, NOV24);
        coded(2, CHART, true, 2, 25_000, NOV24);
        coded(2, ORDER, true, 2, 40_000, NOV24);
        judged(2, null, NOV24);                              // 채점 서버 실패로 점수 없음

        Comparison c = Ghost.report(STEPS, rows).comparison();

        assertThat(row(c, JUDGE).current()).isEqualTo(new Cell(null, null, null));
        assertThat(row(c, JUDGE).improved()).isFalse();
        assertThat(c.improvedSteps()).isZero();
    }
}
