package com.moneymate.overlap;

import com.moneymate.overlap.OverlapDtos.DirectionPair;
import com.moneymate.overlap.OverlapDtos.EtfChange;
import com.moneymate.overlap.OverlapDtos.FilerChange;
import com.moneymate.overlap.OverlapDtos.MyMapConcept;
import com.moneymate.overlap.OverlapDtos.MyMapTicker;
import com.moneymate.overlap.OverlapDtos.NowLinked;
import com.moneymate.overlap.OverlapDtos.NowPrice;
import com.moneymate.overlap.OverlapDtos.NowSource;
import com.moneymate.overlap.OverlapDtos.OverlapList;
import com.moneymate.overlap.OverlapDtos.PathConcept;
import com.moneymate.overlap.OverlapDtos.ReasonEvidence;
import com.moneymate.overlap.OverlapDtos.StockDetail;
import com.moneymate.overlap.OverlapDtos.StockNow;
import com.moneymate.overlap.OverlapDtos.StockOverlap;
import com.moneymate.overlap.OverlapDtos.StockReason;
import com.moneymate.overlap.OverlapDtos.StockReasons;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import tools.jackson.core.JacksonException;

/**
 * 탭2 겹침 목록과 종목 상세 (A, 5~6주차).
 *
 * overlap_results 를 가장 최근 계산일(calc_date) 기준으로 읽어 종목별로 묶기만 한다.
 * 겹침·방향·"몇 명 늘림"은 서버가 다시 계산하지 않는다 (worker/compute/overlap.py 가 정답).
 */
@Service
public class OverlapService {

    private static final Logger log = LoggerFactory.getLogger(OverlapService.class);

    private final OverlapRepository repository;

    public OverlapService(OverlapRepository repository) {
        this.repository = repository;
    }

    public OverlapList list() {
        Optional<LocalDate> calcDate = repository.findLatestCalcDate();
        if (calcDate.isEmpty()) {
            return new OverlapList(null, List.of());
        }
        List<OverlapRow> rows = repository.findRows(calcDate.get(), null);
        return new OverlapList(calcDate.get().toString(), group(rows));
    }

    /**
     * 종목 상세: 겹침(카드 ①) + 카드 ②③(stock_reasons published 최근 분기, 없으면 null)
     * + "내 지도에 있어요". userId 가 null 이면 배운 개념 표시만 빠진다.
     */
    public StockDetail stock(String ticker, String userId) {
        String normalized = normalizeTicker(ticker);
        LocalDate calcDate = repository.findLatestCalcDate().orElseThrow(() -> new StockNotFound(normalized));
        List<StockOverlap> stocks = group(repository.findRows(calcDate, normalized));
        if (stocks.isEmpty()) {
            throw new StockNotFound(normalized);
        }
        StockReasons reasons = repository.findPublishedReasons(normalized)
                .map(row -> reasonsOf(row, userId))
                .orElse(null);
        boolean rejected = reasons == null && isRejected(repository.findLatestReasonsStatus(normalized));
        List<MyMapConcept> mine = userId == null ? List.of() : myConceptsForTicker(userId, normalized);
        return new StockDetail(stocks.get(0), reasons, rejected, mine);
    }

    /**
     * 보여 줄 이유가 없을 때, 가장 최근 분기 이유가 검사에서 전부 버려졌는지(rejected).
     * 예전 분기만 rejected 이고 최근 분기는 아직 안 만들었으면 false (준비 중 문구).
     */
    private static boolean isRejected(Optional<String> latestStatus) {
        return latestStatus.map("rejected"::equals).orElse(false);
    }

    /**
     * stock_reasons 한 줄을 화면 모양으로 옮긴다. 이유를 만들거나 고치지 않고, 경로 개념에 이름과
     * "배운 개념인지"만 붙인다. JSON 이 깨졌으면 이유가 없는 것처럼 null (화면은 대체 문구).
     */
    StockReasons reasonsOf(StockReasonsRow row, String userId) {
        List<StoredReasons.Reason> stored;
        StoredReasons.NowView now;
        try {
            stored = StoredReasons.readReasons(row.reasonsJson());
            now = StoredReasons.readNowView(row.nowViewJson());
        } catch (JacksonException e) {
            log.warn("stock_reasons JSON 을 읽지 못했어요 ({} {}): {}", row.bigPeriodEnd(), row.headline(),
                    e.getOriginalMessage());
            return null;
        }
        Set<String> ids = new LinkedHashSet<>();
        stored.forEach(r -> ids.addAll(nullToEmpty(r.path())));
        Map<String, String> names = new HashMap<>();
        Set<String> learned = new HashSet<>();
        if (!ids.isEmpty()) {
            List<String> idList = List.copyOf(ids);
            repository.findConceptNames(idList).forEach(c -> names.put(c.id(), c.name()));
            if (userId != null) {
                learned.addAll(repository.findLearnedAmong(userId, idList));
            }
        }
        List<StockReason> reasons = stored.stream().map(r -> {
            List<PathConcept> path = nullToEmpty(r.path()).stream()
                    .map(id -> new PathConcept(id, names.getOrDefault(id, id), learned.contains(id)))
                    .toList();
            List<ReasonEvidence> evidence = nullToEmpty(r.evidence()).stream()
                    .map(e -> new ReasonEvidence(e.no(), e.publishedDate(), e.title(), e.issuerName(), e.url()))
                    .toList();
            return new StockReason(r.title(), r.body(), path, r.direction(),
                    path.stream().anyMatch(PathConcept::learned), evidence, r.side());
        }).toList();
        return new StockReasons(str(row.bigPeriodEnd()), row.direction(), row.change(), row.headline(),
                reasons, nowOf(now));
    }

    private static StockNow nowOf(StoredReasons.NowView n) {
        if (n == null) {
            return null;
        }
        StoredReasons.Price p = n.price();
        NowPrice price = p == null ? null
                : new NowPrice(p.fromDate(), p.fromClose(), p.toDate(), p.toClose(), p.returnPct());
        List<NowSource> sources = nullToEmpty(n.laterSources()).stream()
                .map(s -> new NowSource(s.publishedDate(), s.title(), s.url(),
                        s.numbers() == null ? Map.of() : s.numbers()))
                .toList();
        List<NowLinked> linked = nullToEmpty(n.linked()).stream()
                .map(l -> new NowLinked(l.conceptId(), l.name(), l.reasonTitle()))
                .toList();
        return new StockNow(n.baseDate(), price, sources, linked, n.text());
    }

    private static <T> List<T> nullToEmpty(List<T> list) {
        return list == null ? List.of() : list;
    }

    /**
     * "내 지도에 있어요" (#100): 사용자가 배운 개념(total > 0)과 연결된 종목들, 티커 순.
     * 겹침 메인에서 종목마다 배지를 띄울 때 쓴다. 기록이 없거나 연결된 종목이 없으면 빈 목록.
     */
    public List<MyMapTicker> myMapTickers(String userId) {
        Map<String, List<MyMapConcept>> byTicker = new LinkedHashMap<>();
        for (MyMapRow r : repository.findMyMapTickers(userId)) {
            byTicker.computeIfAbsent(r.ticker(), k -> new ArrayList<>()).add(concept(r));
        }
        List<MyMapTicker> out = new ArrayList<>();
        byTicker.forEach((ticker, concepts) -> out.add(new MyMapTicker(ticker, List.copyOf(concepts))));
        return out;
    }

    /** "내 지도에 있어요" (#100): 종목 하나에 연결된 개념 중 사용자가 배운 것, id 순. 종목 상세에서 쓴다. */
    public List<MyMapConcept> myConceptsForTicker(String userId, String ticker) {
        return repository.findMyConceptsForTicker(userId, normalizeTicker(ticker)).stream()
                .map(OverlapService::concept)
                .toList();
    }

    private static MyMapConcept concept(MyMapRow r) {
        return new MyMapConcept(r.conceptId(), r.conceptName(), r.theme());
    }

    /** 경로의 티커를 저장 형식(대문자)에 맞춘다 (conventions 1장). 변환 규칙(P1)은 worker 가 저장할 때 이미 적용했다. */
    static String normalizeTicker(String ticker) {
        return ticker == null ? "" : ticker.trim().toUpperCase(Locale.ROOT);
    }

    /** 행(티커·큰손·ETF 순)을 종목별로 묶는다. 큰손과 ETF 는 처음 나온 순서대로 한 번씩만 넣는다. */
    static List<StockOverlap> group(List<OverlapRow> rows) {
        Map<String, List<OverlapRow>> byTicker = new LinkedHashMap<>();
        for (OverlapRow r : rows) {
            byTicker.computeIfAbsent(r.ticker(), k -> new ArrayList<>()).add(r);
        }
        List<StockOverlap> out = new ArrayList<>();
        byTicker.forEach((ticker, list) -> out.add(stockOf(ticker, list)));
        return out;
    }

    private static StockOverlap stockOf(String ticker, List<OverlapRow> rows) {
        Map<String, FilerChange> filers = new LinkedHashMap<>();
        Map<String, EtfChange> etfs = new LinkedHashMap<>();
        List<DirectionPair> pairs = new ArrayList<>();
        String issuerName = null;
        String etfStockName = null;
        for (OverlapRow r : rows) {
            filers.putIfAbsent(r.filerKey(), new FilerChange(r.filerKey(), r.filerName(), r.changeType(),
                    toDouble(r.bigChgPct()), str(r.bigPeriodEnd()), str(r.filedAt())));
            etfs.putIfAbsent(r.etfCode(), new EtfChange(r.etfCode(), str(r.etfSnapshotDate()),
                    toDouble(r.etfTrendChgPct()), toDouble(r.etfDayChgPct())));
            pairs.add(new DirectionPair(r.filerKey(), r.etfCode(), r.direction()));
            if (issuerName == null) {
                issuerName = r.issuerName();
            }
            if (etfStockName == null) {
                etfStockName = r.etfStockName();
            }
        }
        return new StockOverlap(str(rows.get(0).calcDate()), ticker, issuerName, etfStockName,
                List.copyOf(filers.values()), List.copyOf(etfs.values()), List.copyOf(pairs));
    }

    private static Double toDouble(BigDecimal v) {
        return v == null ? null : v.doubleValue();
    }

    private static String str(LocalDate d) {
        return d == null ? null : d.toString();
    }

    /** 가장 최근 계산일의 겹침 결과에 그 티커가 없다. */
    public static class StockNotFound extends RuntimeException {
        public StockNotFound(String ticker) {
            super("겹침 결과에 없는 종목입니다: " + ticker);
        }
    }
}
