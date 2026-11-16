package com.moneymate.overlap;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.moneymate.overlap.OverlapDtos.DirectionPair;
import com.moneymate.overlap.OverlapDtos.MyMapConcept;
import com.moneymate.overlap.OverlapDtos.MyMapTicker;
import com.moneymate.overlap.OverlapDtos.OverlapList;
import com.moneymate.overlap.OverlapDtos.StockOverlap;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** OverlapService 테스트. DB(OverlapRepository)는 가짜로 바꾼다. SQL 은 OverlapApiIntegrationTest 가 본다. */
class OverlapServiceTest {

    static final LocalDate CALC = LocalDate.of(2026, 11, 14);
    static final LocalDate PERIOD = LocalDate.of(2026, 6, 30);
    static final LocalDate SNAP = LocalDate.of(2026, 11, 13);

    OverlapRepository repo;
    OverlapService service;

    static OverlapRow row(String ticker, String filer, String etf, String direction, String bigChg, String trend) {
        return new OverlapRow(CALC, ticker, filer, PERIOD, bigChg == null ? null : new BigDecimal(bigChg),
                etf, SNAP, trend == null ? null : new BigDecimal(trend), direction,
                filer + " LLC", ticker + " INC", bigChg == null ? "new" : "increase", LocalDate.of(2026, 8, 14),
                null, null);
    }

    @BeforeEach
    void setUp() {
        repo = mock(OverlapRepository.class);
        service = new OverlapService(repo);
    }

    @Test
    void listIsEmptyWhenNoOverlapYet() {
        when(repo.findLatestCalcDate()).thenReturn(Optional.empty());

        assertThat(service.list()).isEqualTo(new OverlapList(null, List.of()));
        verify(repo, never()).findRows(any(), any());
    }

    @Test
    void groupsPairsByTickerWithoutRecomputing() {
        when(repo.findLatestCalcDate()).thenReturn(Optional.of(CALC));
        when(repo.findRows(CALC, null)).thenReturn(List.of(
                row("NVDA", "druckenmiller", "0015B0", "same", "0.1", "0.05"),
                row("NVDA", "druckenmiller", "426030", "diff", "0.1", "-0.16318"),
                row("NVDA", "thiel", "0015B0", "same", null, "0.05"),
                row("NVDA", "thiel", "426030", "diff", null, "-0.16318")));

        OverlapList list = service.list();

        assertThat(list.calcDate()).isEqualTo("2026-11-14");
        StockOverlap nvda = list.stocks().get(0);
        // 큰손·ETF 는 한 번씩, 쌍은 DB 순서 그대로
        assertThat(nvda.filers()).extracting("filerKey").containsExactly("druckenmiller", "thiel");
        assertThat(nvda.filers()).extracting("chgPct").containsExactly(0.1, null);
        assertThat(nvda.etfs()).extracting("trendChgPct").containsExactly(0.05, -0.16318);
        assertThat(nvda.pairs()).containsExactly(
                new DirectionPair("druckenmiller", "0015B0", "same"),
                new DirectionPair("druckenmiller", "426030", "diff"),
                new DirectionPair("thiel", "0015B0", "same"),
                new DirectionPair("thiel", "426030", "diff"));
    }

    @Test
    void stockNormalizesTickerToUppercase() {
        when(repo.findLatestCalcDate()).thenReturn(Optional.of(CALC));
        when(repo.findRows(CALC, "BRK-B")).thenReturn(List.of(row("BRK-B", "buffett", "0015B0", "none", "0", "0.01")));

        assertThat(service.stock(" brk-b ").ticker()).isEqualTo("BRK-B");
    }

    @Test
    void stockNotInOverlapThrows() {
        when(repo.findLatestCalcDate()).thenReturn(Optional.of(CALC));
        when(repo.findRows(eq(CALC), any())).thenReturn(List.of());

        assertThatThrownBy(() -> service.stock("AAPL")).isInstanceOf(OverlapService.StockNotFound.class);
    }

    @Test
    void stockWhenNoOverlapAtAllThrows() {
        when(repo.findLatestCalcDate()).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.stock("NVDA")).isInstanceOf(OverlapService.StockNotFound.class);
    }

    @Test
    void myMapTickersGroupsConceptsByTicker() {
        when(repo.findMyMapTickers("u")).thenReturn(List.of(
                new MyMapRow("MU", "hbm_supply", "HBM 공급 확대", "AI·반도체"),
                new MyMapRow("MU", "memory_price", "D램 가격", "AI·반도체"),
                new MyMapRow("NVDA", "gpu_demand", "AI 반도체 수요", "AI·반도체")));

        assertThat(service.myMapTickers("u")).containsExactly(
                new MyMapTicker("MU", List.of(new MyMapConcept("hbm_supply", "HBM 공급 확대", "AI·반도체"),
                        new MyMapConcept("memory_price", "D램 가격", "AI·반도체"))),
                new MyMapTicker("NVDA", List.of(new MyMapConcept("gpu_demand", "AI 반도체 수요", "AI·반도체"))));
    }

    @Test
    void myConceptsForTickerNormalizesTicker() {
        when(repo.findMyConceptsForTicker("u", "NVDA")).thenReturn(List.of(
                new MyMapRow("NVDA", "gpu_demand", "AI 반도체 수요", "AI·반도체")));

        assertThat(service.myConceptsForTicker("u", " nvda "))
                .containsExactly(new MyMapConcept("gpu_demand", "AI 반도체 수요", "AI·반도체"));
    }
}
