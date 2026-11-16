package com.moneymate.etf;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.moneymate.etf.EtfDtos.EtfDaily;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** EtfService 테스트. DB(EtfRepository)는 가짜로 바꾼다. 기준값 0.05. */
class EtfServiceTest {

    static final LocalDate SNAP = LocalDate.of(2026, 11, 13);
    static final BigDecimal THRESHOLD = new BigDecimal("0.05");

    EtfRepository repo;
    EtfService service;

    static EtfRow snap(String etf) {
        return new EtfRow(etf, SNAP, null, null, null, null);
    }

    static EtfRow row(String etf, String raw, String day) {
        return new EtfRow(etf, SNAP, raw, raw + "-T", raw + " INC", new BigDecimal(day));
    }

    @BeforeEach
    void setUp() {
        repo = mock(EtfRepository.class);
        service = new EtfService(repo, THRESHOLD);
    }

    @Test
    void emptyWhenNoSnapshot() {
        when(repo.findLatestSnapshots()).thenReturn(List.of());
        when(repo.findLatestMoves()).thenReturn(List.of());

        EtfDaily daily = service.daily();

        assertThat(daily.etfs()).isEmpty();
        assertThat(daily.together()).isEmpty();
        assertThat(daily.topIncrease()).isEmpty();
        assertThat(daily.topDecrease()).isEmpty();
    }

    @Test
    void thresholdBoundaryIsIncluded() {
        when(repo.findLatestSnapshots()).thenReturn(List.of(snap("A")));
        when(repo.findLatestMoves()).thenReturn(List.of(
                row("A", "X", "0.05"), row("A", "Y", "0.049999"), row("A", "Z", "-0.05"), row("A", "W", "-0.049999")));

        EtfDaily daily = service.daily();

        assertThat(daily.topIncrease()).extracting("rawCode").containsExactly("X");
        assertThat(daily.topDecrease()).extracting("rawCode").containsExactly("Z");
    }

    @Test
    void topThreeSortedByChange() {
        when(repo.findLatestSnapshots()).thenReturn(List.of(snap("A")));
        when(repo.findLatestMoves()).thenReturn(List.of(
                row("A", "P", "0.06"), row("A", "Q", "0.30"), row("A", "R", "0.10"), row("A", "S", "0.07"),
                row("A", "T", "-0.08"), row("A", "U", "-0.50")));

        EtfDaily daily = service.daily();

        assertThat(daily.topIncrease()).extracting("rawCode").containsExactly("Q", "R", "S");
        assertThat(daily.topDecrease()).extracting("rawCode").containsExactly("U", "T");
    }

    @Test
    void togetherNeedsEveryEtfToIncrease() {
        when(repo.findLatestSnapshots()).thenReturn(List.of(snap("A"), snap("B")));
        when(repo.findLatestMoves()).thenReturn(List.of(
                row("A", "N", "0.08"), row("A", "G", "0.05"), row("B", "N", "0.06"), row("B", "G", "0.01")));

        EtfDaily daily = service.daily();

        assertThat(daily.together()).extracting("rawCode").containsExactly("N");
        assertThat(daily.together().get(0).moves()).extracting("etfCode").containsExactly("A", "B");
    }

    @Test
    void togetherIsEmptyWithSingleEtf() {
        when(repo.findLatestSnapshots()).thenReturn(List.of(snap("A")));
        when(repo.findLatestMoves()).thenReturn(List.of(row("A", "N", "0.08")));

        assertThat(service.daily().together()).isEmpty();
    }
}
