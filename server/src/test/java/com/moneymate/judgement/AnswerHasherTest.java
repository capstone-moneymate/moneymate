package com.moneymate.judgement;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class AnswerHasherTest {

    @Test
    void whitespaceDifferencesAreSameAnswer() {
        assertThat(AnswerHasher.hash(1L, "  금리가  동결\n되어 "))
                .isEqualTo(AnswerHasher.hash(1L, "금리가 동결 되어"));
    }

    @Test
    void differentStepIsDifferentHash() {
        assertThat(AnswerHasher.hash(1L, "같은 답안")).isNotEqualTo(AnswerHasher.hash(2L, "같은 답안"));
    }

    @Test
    void differentTextIsDifferentHash() {
        assertThat(AnswerHasher.hash(1L, "금리 동결")).isNotEqualTo(AnswerHasher.hash(1L, "금리 인하"));
    }

    @Test
    void isSha256Hex() {
        assertThat(AnswerHasher.hash(1L, "답")).hasSize(64).matches("[0-9a-f]+");
    }
}
