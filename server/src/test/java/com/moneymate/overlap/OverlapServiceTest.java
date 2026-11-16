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
import com.moneymate.overlap.OverlapDtos.PathConcept;
import com.moneymate.overlap.OverlapDtos.StockDetail;
import com.moneymate.overlap.OverlapDtos.StockReason;
import com.moneymate.overlap.OverlapDtos.StockReasons;
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

        assertThat(service.stock(" brk-b ", null).overlap().ticker()).isEqualTo("BRK-B");
    }

    @Test
    void stockNotInOverlapThrows() {
        when(repo.findLatestCalcDate()).thenReturn(Optional.of(CALC));
        when(repo.findRows(eq(CALC), any())).thenReturn(List.of());

        assertThatThrownBy(() -> service.stock("AAPL", "u")).isInstanceOf(OverlapService.StockNotFound.class);
        verify(repo, never()).findPublishedReasons(any());   // 404 면 이유를 찾지 않는다
    }

    @Test
    void stockWhenNoOverlapAtAllThrows() {
        when(repo.findLatestCalcDate()).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.stock("NVDA", null)).isInstanceOf(OverlapService.StockNotFound.class);
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

    // ---- 카드 ②③ (#101) ----

    /** reasons.md "저장 모양" 그대로 (snake_case, 화면에 안 내보내는 source_id·errors 포함) */
    static final String REASONS_JSON = """
            [{"title":"AI 투자 확대","body":"…했을 수 있어요.","start_concept":"ai_investment",
              "end_concept":"semi_earnings","path":["ai_investment","gpu_demand","semi_earnings"],"direction":"up",
              "evidence":[{"no":4,"source_id":10,"published_date":"2026-06-12","title":"t","issuer_name":"NVIDIA",
                           "url":"https://a"}]},
             {"title":"금리","body":"b","start_concept":"rate_hike","end_concept":"bond_yield",
              "path":["rate_hike","bond_yield"],"direction":"up","evidence":[]}]""";
    static final String NOW_JSON = """
            {"base_date":"2026-06-30","price":{"from_date":"2026-06-30","from_close":100.0,"to_date":"2026-11-14",
             "to_close":112.5,"return_pct":12.5},"later_sources":[{"source_id":55,"published_date":"2026-11-12",
             "title":"실적","url":"https://b","numbers":{"매출액 전년동기대비(%)":62.0}}],
             "linked":[{"concept_id":"gpu_demand","name":"AI 반도체 수요","reason_title":"AI 투자 확대"}],
             "text":"기준일 뒤 주가는 12.5% 올랐어요.","errors":["x"]}""";

    void stockExists() {
        when(repo.findLatestCalcDate()).thenReturn(Optional.of(CALC));
        when(repo.findRows(CALC, "NVDA")).thenReturn(List.of(row("NVDA", "thiel", "0015B0", "same", null, "0.05")));
    }

    @Test
    void reasonsGetConceptNamesAndMyMapFlags() {
        stockExists();
        when(repo.findPublishedReasons("NVDA")).thenReturn(Optional.of(new StockReasonsRow(
                PERIOD, "same", "up", "왜 다 늘렸을까요?", REASONS_JSON, NOW_JSON)));
        when(repo.findConceptNames(any())).thenReturn(List.of(new ConceptNameRow("ai_investment", "AI 데이터센터 투자"),
                new ConceptNameRow("gpu_demand", "AI 반도체 수요"), new ConceptNameRow("semi_earnings", "반도체 기업 실적"),
                new ConceptNameRow("rate_hike", "기준금리 인상")));
        when(repo.findLearnedAmong(eq("u"), any())).thenReturn(List.of("gpu_demand"));

        StockReasons r = service.stock("nvda", "u").reasons();

        assertThat(r.bigPeriodEnd()).isEqualTo("2026-06-30");
        assertThat(r.headline()).isEqualTo("왜 다 늘렸을까요?");
        StockReason first = r.reasons().get(0);
        // 경로에 배운 개념(gpu_demand)이 있어 "내 지도에 있어요"
        assertThat(first.path()).containsExactly(new PathConcept("ai_investment", "AI 데이터센터 투자", false),
                new PathConcept("gpu_demand", "AI 반도체 수요", true),
                new PathConcept("semi_earnings", "반도체 기업 실적", false));
        assertThat(first.inMyMap()).isTrue();
        assertThat(first.evidence()).extracting("no", "publishedDate", "issuerName").containsExactly(
                org.assertj.core.groups.Tuple.tuple(4, "2026-06-12", "NVIDIA"));
        // 사전에 이름이 없는 개념(bond_yield)은 id 그대로, 배운 개념 없음
        StockReason second = r.reasons().get(1);
        assertThat(second.path()).extracting("name").containsExactly("기준금리 인상", "bond_yield");
        assertThat(second.inMyMap()).isFalse();
        // 경로 개념 id 를 한 번씩만 묻는다
        verify(repo).findConceptNames(List.of("ai_investment", "gpu_demand", "semi_earnings", "rate_hike", "bond_yield"));
        // 카드 ③: 값은 그대로, errors 는 내보내지 않는다 (DTO 에 칸이 없음)
        assertThat(r.now().price().returnPct()).isEqualTo(12.5);
        assertThat(r.now().laterSources().get(0).numbers()).containsEntry("매출액 전년동기대비(%)", 62.0);
        assertThat(r.now().linked()).extracting("conceptId").containsExactly("gpu_demand");
        assertThat(r.now().text()).isEqualTo("기준일 뒤 주가는 12.5% 올랐어요.");
    }

    @Test
    void withoutUserIdNoLearnedLookup() {
        stockExists();
        when(repo.findPublishedReasons("NVDA")).thenReturn(Optional.of(new StockReasonsRow(
                PERIOD, "same", "up", "h", REASONS_JSON, null)));

        StockDetail d = service.stock("NVDA", null);

        assertThat(d.reasons().reasons()).allMatch(x -> !x.inMyMap());
        assertThat(d.reasons().now()).isNull();   // 카드 ③ 아직 없음
        assertThat(d.myConcepts()).isEmpty();
        verify(repo, never()).findLearnedAmong(any(), any());
        verify(repo, never()).findMyConceptsForTicker(any(), any());
    }

    @Test
    void noPublishedReasonsIsNullAndMyConceptsStillCome() {
        stockExists();
        when(repo.findMyConceptsForTicker("u", "NVDA")).thenReturn(List.of(
                new MyMapRow("NVDA", "gpu_demand", "AI 반도체 수요", "AI·반도체")));

        StockDetail d = service.stock("NVDA", "u");

        assertThat(d.reasons()).isNull();
        assertThat(d.myConcepts()).containsExactly(new MyMapConcept("gpu_demand", "AI 반도체 수요", "AI·반도체"));
    }

    @Test
    void brokenReasonsJsonActsLikeNoReasons() {
        stockExists();
        when(repo.findPublishedReasons("NVDA")).thenReturn(Optional.of(new StockReasonsRow(
                PERIOD, "same", "up", "h", "[{\"title\":", null)));

        assertThat(service.stock("NVDA", null).reasons()).isNull();
    }
}
