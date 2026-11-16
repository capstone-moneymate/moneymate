package com.moneymate.learning;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/** ConceptResultRecorder 테스트. DB(LearningRepository)는 가짜로 바꾼다. SQL 은 실제 DB 로 따로 확인 (명세 참고). */
class ConceptResultRecorderTest {

    static final String USER = "11111111-2222-3333-4444-555555555555";

    LearningRepository repo;
    ConceptResultRecorder recorder;

    @BeforeEach
    void setUp() {
        repo = mock(LearningRepository.class);
        recorder = new ConceptResultRecorder(repo);
    }

    String[] sentIds() {
        ArgumentCaptor<String[]> ids = ArgumentCaptor.forClass(String[].class);
        verify(repo).upsertConceptResults(eq(USER), ids.capture(), anyBoolean());
        return ids.getValue();
    }

    @Test
    void correctAnswerIsRecordedAsCorrect() {
        String[] ids = {"rate_hold", "loan_spread", "bank_profit"};
        when(repo.upsertConceptResults(USER, ids, true)).thenReturn(3);

        int n = recorder.recordConceptResult(USER, ids, true);

        assertThat(n).isEqualTo(3);
        verify(repo).ensureUser(USER);
        verify(repo).upsertConceptResults(USER, ids, true);
    }

    @Test
    void wrongAnswerIsRecordedAsWrong() {
        when(repo.upsertConceptResults(eq(USER), any(), eq(false))).thenReturn(1);

        recorder.recordConceptResult(USER, new String[] {"rate_hold"}, false);

        verify(repo).upsertConceptResults(USER, new String[] {"rate_hold"}, false);
    }

    @Test
    void nullResultIsNotRecorded() {
        // 판단 채점을 못 했을 때 (JudgementResponse.correct == null)
        int n = recorder.recordConceptResult(USER, new String[] {"rate_hold"}, null);

        assertThat(n).isZero();
        verifyNoInteractions(repo);
    }

    @Test
    void emptyOrNullIdsAreNotRecorded() {
        assertThat(recorder.recordConceptResult(USER, null, true)).isZero();
        assertThat(recorder.recordConceptResult(USER, new String[] {}, true)).isZero();
        assertThat(recorder.recordConceptResult(USER, new String[] {null, " "}, false)).isZero();

        verifyNoInteractions(repo);
    }

    @Test
    void duplicateIdsAreCountedOnceInOrder() {
        when(repo.upsertConceptResults(anyString(), any(), anyBoolean())).thenReturn(2);

        recorder.recordConceptResult(USER, new String[] {"rate_hold", " rate_hold ", "bank_profit", "rate_hold"}, true);

        assertThat(sentIds()).containsExactly("rate_hold", "bank_profit");
    }

    @Test
    void unknownIdsAreSkippedWithoutError() {
        // concepts 에 없는 id 는 SQL 이 건너뛰어 기록 수가 줄어든다. 예외 없이 기록한 수만 돌려준다
        when(repo.upsertConceptResults(anyString(), any(), anyBoolean())).thenReturn(1);

        int n = recorder.recordConceptResult(USER, new String[] {"rate_hold", "no_such_concept"}, true);

        assertThat(n).isEqualTo(1);
    }

    @Test
    void ensureUserIsSkippedWhenNothingToRecord() {
        recorder.recordConceptResult(USER, new String[] {}, true);

        verify(repo, never()).ensureUser(anyString());
    }
}
