package com.moneymate.mypage;

import com.moneymate.mypage.MypageDtos.CausalMap;
import com.moneymate.mypage.MypageDtos.MapEdge;
import com.moneymate.mypage.MypageDtos.MapNode;
import com.moneymate.mypage.MypageDtos.Review;
import com.moneymate.mypage.MypageDtos.ReviewConcept;
import com.moneymate.mypage.MypageDtos.Summary;
import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * 탭3 인과 지도와 다시 보는 개념 (B, 5주차). DB 읽기만 한다.
 *
 * 인과 지도: 배운 개념(total > 0)과, 한쪽 끝이라도 배운 개념에 닿은 사전 연결 전부.
 * 연결의 반대쪽 끝이 아직 안 배운 개념이면 learned=false 점으로 같이 내려 준다.
 * "이 경로가 정답"이 아니라 "이런 흐름이 가능하다"를 보여 주려고, 배운 개념에서 한 걸음 뻗은 가지까지 그린다.
 *
 * 다시 보는 개념: total > 0 인 개념 전부. 정답률 낮은 순 → 푼 횟수 적은 순 → id 순.
 * 기록이 없으면 빈 배열 (users 에 행을 넣지 않는다).
 *
 * 홈 숫자(summary): 연속 학습(KST), 배운 개념 수, 종합 정답률(user_answers 의 is_correct), 판단해보기 횟수.
 */
@Service
public class MypageService {

    /** 정답률 낮은 순 → 푼 횟수 적은 순 → id 순. 정답률은 나눗셈 대신 교차 곱으로 비교해 소수 오차가 없다. */
    static final Comparator<ConceptRow> REVIEW_ORDER = ((Comparator<ConceptRow>) (a, b) ->
            Long.compare((long) a.correct() * b.total(), (long) b.correct() * a.total()))
            .thenComparingInt(ConceptRow::total)
            .thenComparing(ConceptRow::id);

    static final ZoneId KST = ZoneId.of("Asia/Seoul");

    private final MypageRepository repository;
    private final Clock clock;

    @Autowired
    public MypageService(MypageRepository repository) {
        this(repository, Clock.system(KST));
    }

    MypageService(MypageRepository repository, Clock clock) {
        this.repository = repository;
        this.clock = clock;
    }

    public CausalMap map(String userId) {
        List<ConceptRow> learned = repository.findLearnedConcepts(userId);
        if (learned.isEmpty()) {
            return new CausalMap(List.of(), List.of());
        }
        List<EdgeRow> edges = repository.findEdgesTouchingLearned(userId);

        Set<String> learnedIds = new LinkedHashSet<>();
        learned.forEach(c -> learnedIds.add(c.id()));
        Set<String> neighborIds = new LinkedHashSet<>();
        for (EdgeRow e : edges) {
            if (!learnedIds.contains(e.from())) {
                neighborIds.add(e.from());
            }
            if (!learnedIds.contains(e.to())) {
                neighborIds.add(e.to());
            }
        }
        List<ConceptRow> neighbors = neighborIds.isEmpty()
                ? List.of() : repository.findConcepts(List.copyOf(neighborIds));

        List<MapNode> nodes = new ArrayList<>();
        learned.forEach(c -> nodes.add(new MapNode(c.id(), c.name(), c.theme(), c.correct(), c.total(), true)));
        neighbors.forEach(c -> nodes.add(new MapNode(c.id(), c.name(), c.theme(), 0, 0, false)));
        nodes.sort(Comparator.comparing(MapNode::id));

        List<MapEdge> out = edges.stream().map(e -> new MapEdge(e.from(), e.to(), e.forceDir())).toList();
        return new CausalMap(nodes, out);
    }

    public Review review(String userId) {
        List<ReviewConcept> concepts = repository.findLearnedConcepts(userId).stream()
                .filter(c -> c.total() > 0)
                .sorted(REVIEW_ORDER)
                .map(c -> new ReviewConcept(c.id(), c.name(), c.theme(), c.correct(), c.total(), accuracy(c)))
                .toList();
        return new Review(concepts);
    }

    /** correct / total (소수, 0.5 = 50%). total 이 0 이면 0. */
    static double accuracy(ConceptRow c) {
        return c.total() == 0 ? 0.0 : (double) c.correct() / c.total();
    }

    public Summary summary(String userId) {
        LocalDate today = LocalDate.now(clock.withZone(KST));
        List<LocalDate> days = repository.findAnswerDays(userId);
        AnswerCounts counts = repository.countAnswers(userId);
        int concepts = repository.findLearnedConcepts(userId).size();
        Double accuracy = counts.graded() == 0 ? null : (double) counts.correct() / counts.graded();
        return new Summary(streak(days, today), days.contains(today), concepts, accuracy,
                counts.graded(), counts.judgements());
    }

    /**
     * 연속 학습 일수. days 는 답안을 낸 KST 날짜(순서·중복 상관없음).
     * 오늘 풀었으면 오늘부터, 오늘 아직 안 풀었으면 어제부터 거꾸로 하루씩 이어진 날을 센다.
     * (오늘 하루 동안은 끊긴 것으로 치지 않는다. 오늘 끝까지 안 풀면 내일 0 이 된다)
     */
    static int streak(List<LocalDate> days, LocalDate today) {
        Set<LocalDate> set = Set.copyOf(days);
        LocalDate d = set.contains(today) ? today : today.minusDays(1);
        int n = 0;
        while (set.contains(d)) {
            n++;
            d = d.minusDays(1);
        }
        return n;
    }
}
