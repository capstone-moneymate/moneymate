package com.moneymate.mypage;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.moneymate.mypage.MypageDtos.CausalMap;
import com.moneymate.mypage.MypageDtos.MapEdge;
import com.moneymate.mypage.MypageDtos.MapNode;
import com.moneymate.mypage.MypageDtos.ReviewConcept;
import com.moneymate.mypage.MypageDtos.Summary;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import org.assertj.core.data.Offset;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** MypageService 테스트. DB(MypageRepository)는 가짜로 바꾸고, 연결은 실제 사전(db/seeds/causal_edges.csv)에서 가져왔다. */
class MypageServiceTest {

    static final String USER = "11111111-2222-3333-4444-555555555555";

    MypageRepository repo;
    MypageService service;

    static ConceptRow learned(String id, int correct, int total) {
        return new ConceptRow(id, id + " 이름", "금리", correct, total);
    }

    static ConceptRow plain(String id) {
        return new ConceptRow(id, id + " 이름", "금리", 0, 0);
    }

    @BeforeEach
    void setUp() {
        repo = mock(MypageRepository.class);
        service = new MypageService(repo);
    }

    // --- 인과 지도 ---

    @Test
    void mapIncludesOneStepNeighborsAsNotLearned() {
        // 손계산: rate_hike 만 배움(2/3). 사전에서 rate_hike 에 닿은 연결은 3개
        //   inflation → rate_hike (up), rate_hike → bond_yield (up), rate_hike → bank_margin (up)
        //   → 점 4개: rate_hike(배움) + inflation·bond_yield·bank_margin(안 배움, 0/0), id 순
        when(repo.findLearnedConcepts(USER)).thenReturn(List.of(learned("rate_hike", 2, 3)));
        when(repo.findEdgesTouchingLearned(USER)).thenReturn(List.of(
                new EdgeRow("inflation", "rate_hike", "up"),
                new EdgeRow("rate_hike", "bond_yield", "up"),
                new EdgeRow("rate_hike", "bank_margin", "up")));
        when(repo.findConcepts(List.of("inflation", "bond_yield", "bank_margin")))
                .thenReturn(List.of(plain("bank_margin"), plain("bond_yield"), plain("inflation")));

        CausalMap map = service.map(USER);

        assertThat(map.nodes()).extracting(MapNode::id)
                .containsExactly("bank_margin", "bond_yield", "inflation", "rate_hike");
        assertThat(map.nodes().get(3)).isEqualTo(new MapNode("rate_hike", "rate_hike 이름", "금리", 2, 3, true));
        assertThat(map.nodes().get(0)).isEqualTo(new MapNode("bank_margin", "bank_margin 이름", "금리", 0, 0, false));
        assertThat(map.nodes()).filteredOn(n -> !n.learned()).hasSize(3);
        assertThat(map.edges()).containsExactly(
                new MapEdge("inflation", "rate_hike", "up"),
                new MapEdge("rate_hike", "bond_yield", "up"),
                new MapEdge("rate_hike", "bank_margin", "up"));
    }

    @Test
    void learnedConceptIsNotDuplicatedAsNeighbor() {
        // rate_hike, bond_yield 둘 다 배움. 둘을 잇는 연결의 끝은 이웃으로 다시 찾지 않는다
        when(repo.findLearnedConcepts(USER)).thenReturn(List.of(learned("bond_yield", 1, 1), learned("rate_hike", 0, 2)));
        when(repo.findEdgesTouchingLearned(USER)).thenReturn(List.of(
                new EdgeRow("inflation", "rate_hike", "up"),
                new EdgeRow("rate_hike", "bond_yield", "up"),
                new EdgeRow("rate_cut", "bond_yield", "down")));
        when(repo.findConcepts(List.of("inflation", "rate_cut"))).thenReturn(List.of(plain("inflation"), plain("rate_cut")));

        CausalMap map = service.map(USER);

        assertThat(map.nodes()).extracting(MapNode::id)
                .containsExactly("bond_yield", "inflation", "rate_cut", "rate_hike");
        assertThat(map.nodes()).extracting(MapNode::learned).containsExactly(true, false, false, true);
        assertThat(map.edges()).extracting(MapEdge::forceDir).containsExactly("up", "up", "down");
        verify(repo).findConcepts(List.of("inflation", "rate_cut"));
    }

    @Test
    void learnedConceptWithoutEdgesIsAloneOnMap() {
        // 차트 읽기 개념처럼 사전 연결이 없는 개념만 배웠으면 점 1개, 화살표 0개
        when(repo.findLearnedConcepts(USER)).thenReturn(List.of(learned("volume_spike", 1, 2)));
        when(repo.findEdgesTouchingLearned(USER)).thenReturn(List.of());

        CausalMap map = service.map(USER);

        assertThat(map.nodes()).extracting(MapNode::id).containsExactly("volume_spike");
        assertThat(map.edges()).isEmpty();
        verify(repo, never()).findConcepts(anyList());
    }

    @Test
    void mapForUserWithoutRecordsIsEmpty() {
        when(repo.findLearnedConcepts(USER)).thenReturn(List.of());

        CausalMap map = service.map(USER);

        assertThat(map.nodes()).isEmpty();
        assertThat(map.edges()).isEmpty();
        verify(repo, never()).findEdgesTouchingLearned(anyString());
        verify(repo, never()).findConcepts(anyList());
    }

    // --- 다시 보는 개념 ---

    @Test
    void reviewSortsByAccuracyThenFewerAttemptsThenId() {
        // 손계산 정답률: a 0/1=0, b 0/3=0, c 1/4=0.25, g 1/3=0.333, x 1/2=0.5, d 1/2=0.5, e 2/4=0.5, f 3/3=1
        //   정답률 낮은 순 → 같으면 푼 횟수 적은 순(a 1번 < b 3번, d·x 2번 < e 4번) → 같으면 id 순(d < x)
        when(repo.findLearnedConcepts(USER)).thenReturn(List.of(
                learned("f", 3, 3), learned("e", 2, 4), learned("x", 1, 2), learned("d", 1, 2),
                learned("g", 1, 3), learned("c", 1, 4), learned("b", 0, 3), learned("a", 0, 1)));

        List<ReviewConcept> out = service.review(USER).concepts();

        assertThat(out).extracting(ReviewConcept::id).containsExactly("a", "b", "c", "g", "d", "x", "e", "f");
        assertThat(out.get(2).accuracy()).isEqualTo(0.25);
        assertThat(out.get(3).accuracy()).isCloseTo(0.3333333, Offset.offset(1e-6));
        assertThat(out.get(7).accuracy()).isEqualTo(1.0);
        assertThat(out.get(0)).isEqualTo(new ReviewConcept("a", "a 이름", "금리", 0, 1, 0.0));
    }

    @Test
    void reviewSkipsZeroTotalAndEmptyUser() {
        // SQL 이 total > 0 만 주지만, 0 이 섞여 와도 목록에 넣지 않는다 (0 으로 나누지 않음)
        when(repo.findLearnedConcepts(USER)).thenReturn(List.of(learned("a", 0, 0), learned("b", 1, 2)));
        assertThat(service.review(USER).concepts()).extracting(ReviewConcept::id).containsExactly("b");

        when(repo.findLearnedConcepts(USER)).thenReturn(List.of());
        assertThat(service.review(USER).concepts()).isEmpty();
    }

    @Test
    void accuracyIsDecimal() {
        assertThat(MypageService.accuracy(learned("a", 3, 4))).isEqualTo(0.75);
        assertThat(MypageService.accuracy(learned("a", 0, 0))).isEqualTo(0.0);
    }

    // --- 홈 숫자 (summary) ---

    static final LocalDate TODAY = LocalDate.of(2026, 11, 19); // 목요일

    static List<LocalDate> days(String... isoDates) {
        return java.util.Arrays.stream(isoDates).map(LocalDate::parse).toList();
    }

    @Test
    void streakCountsFromTodayWhenStudiedToday() {
        // 손계산: 월(16)·화(17)·수(18)·목(19=오늘) → 4일. 14일(토)은 15일이 비어서 끊김
        assertThat(MypageService.streak(days("2026-11-19", "2026-11-18", "2026-11-17", "2026-11-16", "2026-11-14"), TODAY))
                .isEqualTo(4);
    }

    @Test
    void streakCountsFromYesterdayWhenNotYetToday() {
        // 오늘(19) 아직 안 풂: 어제(18)부터 18·17·16 → 3일 (오늘 하루 동안은 끊긴 것으로 치지 않음)
        assertThat(MypageService.streak(days("2026-11-18", "2026-11-17", "2026-11-16"), TODAY)).isEqualTo(3);
    }

    @Test
    void streakIsZeroWhenYesterdayMissing() {
        // 어제(18)도 안 풂 → 0. 17·16 기록은 이미 끊긴 것
        assertThat(MypageService.streak(days("2026-11-17", "2026-11-16"), TODAY)).isZero();
        assertThat(MypageService.streak(List.of(), TODAY)).isZero();
    }

    @Test
    void streakIgnoresOrderAndFutureDays() {
        // 순서가 섞여도 같은 값. 오늘 뒤 날짜(시계 차이)는 세지 않음
        assertThat(MypageService.streak(days("2026-11-17", "2026-11-20", "2026-11-19", "2026-11-18"), TODAY)).isEqualTo(3);
    }

    @Test
    void summaryUsesKstToday() {
        // 2026-11-18T15:30Z = KST 11/19 00:30. KST 로는 이미 목요일이라 19일 기록이 "오늘"
        Clock clock = Clock.fixed(Instant.parse("2026-11-18T15:30:00Z"), ZoneOffset.UTC);
        MypageService kst = new MypageService(repo, clock);
        when(repo.findAnswerDays(USER)).thenReturn(days("2026-11-19", "2026-11-18"));
        when(repo.countAnswers(USER)).thenReturn(new AnswerCounts(8, 6, 2));
        when(repo.findLearnedConcepts(USER)).thenReturn(List.of(learned("a", 1, 2), learned("b", 3, 3)));

        Summary s = kst.summary(USER);

        // 손계산: 연속 2일(19·18), 오늘 풂, 개념 2개, 정답률 6/8 = 0.75, 채점 8개, 판단 2회
        assertThat(s).isEqualTo(new Summary(2, true, 2, 0.75, 8, 2));
    }

    @Test
    void summaryForEmptyUser() {
        MypageService fixed = new MypageService(repo,
                Clock.fixed(Instant.parse("2026-11-19T03:00:00Z"), ZoneOffset.UTC));
        when(repo.findAnswerDays(USER)).thenReturn(List.of());
        when(repo.countAnswers(USER)).thenReturn(new AnswerCounts(0, 0, 0));
        when(repo.findLearnedConcepts(USER)).thenReturn(List.of());

        // 채점된 답안이 없으면 정답률은 null (0% 로 보이지 않게)
        assertThat(fixed.summary(USER)).isEqualTo(new Summary(0, false, 0, null, 0, 0));
    }
}
