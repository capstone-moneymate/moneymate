package com.moneymate.news;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.moneymate.news.NewsDtos.CardDetail;
import com.moneymate.news.NewsDtos.MarketIndex;
import com.moneymate.news.NewsDtos.NewsHome;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** NewsService 테스트. DB(NewsRepository)는 가짜로 바꾼다. */
class NewsServiceTest {

    static final String USER = "11111111-2222-3333-4444-555555555555";
    // 2026-11-07 00:30 KST (= 11-06 15:30 UTC). KST 기준 오늘은 11-07
    static final Clock CLOCK = Clock.fixed(Instant.parse("2026-11-06T15:30:00Z"), ZoneOffset.UTC);
    static final LocalDate TODAY = LocalDate.of(2026, 11, 7);
    static final String SLIDES = """
            [{"label":"무슨 일이 있었나요?","heading":"동결","body":"한국은행이 기준금리를 3.00%로 그대로 뒀어요.",
              "facts":[{"label":"기준금리","value":"3.00%"}]},
             {"label":"오늘의 결론","heading":"정리","body":"은행주가 올랐어요."}]""";

    NewsRepository repo;
    NewsService service;

    static CardRow card(long id, String sourceType, String issuer, OffsetDateTime at, LocalDate date) {
        return new CardRow(id, 2, LocalDate.of(2026, 11, 6), "기준금리 동결", "금리", null, SLIDES,
                sourceType, issuer, "https://www.bok.or.kr/", at, date, 5);
    }

    @BeforeEach
    void setUp() {
        repo = mock(NewsRepository.class);
        service = new NewsService(repo, false, CLOCK);
        when(repo.findLatestIndices(anyList())).thenReturn(List.of());
    }

    // --- 홈 ---

    @Test
    void homeUsesLatestCardDateUpToTodayKst() {
        LocalDate cardDate = LocalDate.of(2026, 11, 6);
        when(repo.findLatestCardDate(TODAY, false)).thenReturn(Optional.of(cardDate));
        when(repo.findCardsByDate(cardDate, false)).thenReturn(List.of(
                card(3, "macro", "한국은행", OffsetDateTime.parse("2026-11-06T10:30:00+09:00"), cardDate)));

        NewsHome home = service.home(null);

        assertThat(home.date()).isEqualTo("2026-11-06");
        assertThat(home.cards()).hasSize(1);
        var c = home.cards().get(0);
        assertThat(c.id()).isEqualTo("3");
        assertThat(c.type()).isEqualTo(2);
        assertThat(c.summary()).isEqualTo("한국은행이 기준금리를 3.00%로 그대로 뒀어요.");
        assertThat(c.theme()).isEqualTo("금리");
        assertThat(c.sourceName()).isEqualTo("한국은행");          // 거시 발표는 기관 이름만
        assertThat(c.sourcePublishedAt()).isEqualTo("2026-11-06T01:30:00Z");   // KST 10:30 → UTC
        assertThat(c.stepCount()).isEqualTo(5);
        // userId 가 없으면 완료 카드를 묻지 않는다
        assertThat(home.completedCardIds()).isEmpty();
        verify(repo, never()).findCompletedCardIds(anyString(), anyList());
    }

    @Test
    void homeWithoutCardsFallsBackToToday() {
        when(repo.findLatestCardDate(any(), anyBoolean())).thenReturn(Optional.empty());
        when(repo.findCardsByDate(TODAY, false)).thenReturn(List.of());

        NewsHome home = service.home(USER);

        assertThat(home.date()).isEqualTo("2026-11-07");
        assertThat(home.cards()).isEmpty();
        assertThat(home.completedCardIds()).isEmpty();
        verify(repo, never()).findCompletedCardIds(anyString(), anyList());
    }

    @Test
    void homeReturnsCompletedCardIdsAsStrings() {
        LocalDate d = LocalDate.of(2026, 11, 6);
        when(repo.findLatestCardDate(TODAY, false)).thenReturn(Optional.of(d));
        when(repo.findCardsByDate(d, false)).thenReturn(List.of(card(3, null, null, null, null),
                card(4, null, null, null, null)));
        when(repo.findCompletedCardIds(USER, List.of(3L, 4L))).thenReturn(List.of(4L));

        assertThat(service.home(USER).completedCardIds()).containsExactly("4");
    }

    @Test
    void includePendingIsPassedToRepository() {
        NewsService pending = new NewsService(repo, true, CLOCK);
        when(repo.findLatestCardDate(TODAY, true)).thenReturn(Optional.of(TODAY));
        when(repo.findCardsByDate(TODAY, true)).thenReturn(List.of());

        pending.home(null);

        verify(repo).findLatestCardDate(TODAY, true);
        verify(repo).findCardsByDate(TODAY, true);
    }

    @Test
    void indicesInScreenOrderWithChangeRate() {
        // 손계산: KOSPI (2987.42 - 2951.12) / 2951.12 = 0.0123004...
        //         NASDAQ 전날이 없으면 chgPct null
        List<MarketIndex> out = service.indices(List.of(
                new IndexRow("IXIC", LocalDate.of(2026, 11, 5), new BigDecimal("18542.9"), null),
                new IndexRow("KS11", LocalDate.of(2026, 11, 6), new BigDecimal("2987.42"), new BigDecimal("2951.12"))));

        assertThat(out).extracting(MarketIndex::code).containsExactly("KS11", "IXIC");   // KQ11·US500 은 데이터 없음
        assertThat(out.get(0).name()).isEqualTo("KOSPI");
        assertThat(out.get(0).value()).isEqualTo(2987.42);
        assertThat(out.get(0).chgPct()).isCloseTo(0.0123004, org.assertj.core.data.Offset.offset(1e-6));
        assertThat(out.get(0).date()).isEqualTo("2026-11-06");
        assertThat(out.get(1).chgPct()).isNull();
    }

    @Test
    void chgPctNullWhenPrevIsZero() {
        assertThat(NewsService.chgPct(BigDecimal.ONE, BigDecimal.ZERO)).isNull();
        assertThat(NewsService.chgPct(new BigDecimal("99"), new BigDecimal("100"))).isEqualTo(-0.01);
    }

    @Test
    void summaryIsCutAt80Chars() {
        String body = "가".repeat(100);
        String slides = "[{\"label\":\"무슨 일이 있었나요?\",\"heading\":\"h\",\"body\":\"" + body + "\"}]";
        assertThat(service.summaryText(slides)).isEqualTo("가".repeat(80) + "…");
        assertThat(service.summaryText("[]")).isEmpty();
        assertThat(service.summaryText("깨진 JSON")).isEmpty();
    }

    @Test
    void sourceNameAndDateFallbacks() {
        // 공시: "DART · 회사", DART 는 시각이 없어 그날 0시 KST
        CardRow dart = card(1, "dart", "SK하이닉스", null, LocalDate.of(2026, 11, 6));
        assertThat(NewsService.sourceName(dart)).isEqualTo("DART · SK하이닉스");
        assertThat(NewsService.sourcePublishedAt(dart)).isEqualTo("2026-11-05T15:00:00Z");
        assertThat(NewsService.sourceName(card(1, "sec_8k", "NVIDIA", null, null))).isEqualTo("SEC 8-K · NVIDIA");
        // 대표 자료가 없고 source_links 이름만 있으면 그 이름
        assertThat(NewsService.sourceName(card(1, null, "한국은행", null, null))).isEqualTo("한국은행");
        assertThat(NewsService.sourcePublishedAt(card(1, null, null, null, null))).isNull();
    }

    // --- 카드 상세 ---

    @Test
    void cardDetailCamelCasesAndHidesAnswers() {
        when(repo.findCard(3L, false)).thenReturn(Optional.of(
                new CardRow(3, 3, LocalDate.of(2026, 11, 6), "HBM 공급 계약", "AI·반도체", "NVDA", SLIDES,
                        "dart", "SK하이닉스", "https://dart.fss.or.kr/", null, LocalDate.of(2026, 11, 6), 3)));
        when(repo.findSteps(3L)).thenReturn(List.of(
                new StepRow(10, 1, "causal_order", """
                        {"concept_ids":["hbm_demand","memory_price"],"question":"순서대로 놓아 보세요",
                         "items":[{"concept_id":"memory_price","label":"메모리 가격"},
                                  {"concept_id":"hbm_demand","label":"HBM 수요"}]}"""),
                new StepRow(11, 2, "chart", """
                        {"concept_ids":["volume"],"question":"거래량은?","options":["늘었다","줄었다"],
                         "ticker":"000660","start_date":"2026-08-01","end_date":"2026-11-06",
                         "answer_index":0,"explanation":"섞여 들어온 정답","chart_check":{"metric":"volume"}}"""),
                new StepRow(12, 3, "judgement", """
                        {"concept_ids":[],"question":"어떻게 볼까요?","context":"ETF가 늘렸어요",
                         "choices":["좋다","관망"],"chain":["hbm_demand"],"counter":["rate_hike"]}""")));

        CardDetail d = service.card(3L);

        assertThat(d.id()).isEqualTo("3");
        assertThat(d.type()).isEqualTo(3);
        assertThat(d.ticker()).isEqualTo("NVDA");
        assertThat(d.sourceName()).isEqualTo("DART · SK하이닉스");
        assertThat(d.slides()).hasSize(2);
        assertThat(d.slides().get(0)).containsEntry("label", "무슨 일이 있었나요?");
        assertThat(d.slides().get(0).get("facts")).isEqualTo(List.of(Map.of("label", "기준금리", "value", "3.00%")));

        Map<String, Object> order = d.steps().get(0);
        assertThat(order).containsEntry("id", "10").containsEntry("no", 1).containsEntry("kind", "causal_order");
        assertThat(order.get("conceptIds")).isEqualTo(List.of("hbm_demand", "memory_price"));
        assertThat(order.get("items")).isEqualTo(List.of(
                Map.of("conceptId", "memory_price", "label", "메모리 가격"),
                Map.of("conceptId", "hbm_demand", "label", "HBM 수요")));

        Map<String, Object> chart = d.steps().get(1);
        assertThat(chart).containsEntry("startDate", "2026-08-01").containsEntry("endDate", "2026-11-06")
                .containsEntry("ticker", "000660");
        assertThat(chart).doesNotContainKeys("answerIndex", "answer_index", "explanation", "chartCheck", "chart_check");

        Map<String, Object> judge = d.steps().get(2);
        assertThat(judge.get("choices")).isEqualTo(List.of("좋다", "관망"));
        assertThat(judge).doesNotContainKeys("chain", "counter");
        // 어떤 단계에도 snake_case 키가 남지 않는다
        d.steps().forEach(s -> assertThat(s.keySet()).noneMatch(k -> k.contains("_")));
    }

    @Test
    void stepWithoutConceptIdsGetsEmptyList() {
        Map<String, Object> s = service.step(new StepRow(1, 1, "concept", "{\"title\":\"t\",\"body\":\"b\",\"terms\":[]}"));
        assertThat(s.get("conceptIds")).isEqualTo(List.of());
    }

    @Test
    void missingOrHiddenCardIs404() {
        when(repo.findCard(eq(99L), anyBoolean())).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.card(99L)).isInstanceOf(NewsService.CardNotFound.class);
        verify(repo, never()).findSteps(99L);
    }

    @Test
    void toCamelConvertsSnakeKeys() {
        assertThat(NewsService.toCamel("concept_ids")).isEqualTo("conceptIds");
        assertThat(NewsService.toCamel("start_date")).isEqualTo("startDate");
        assertThat(NewsService.toCamel("label")).isEqualTo("label");
        assertThat(NewsService.toCamel("conceptIds")).isEqualTo("conceptIds");
    }
}
