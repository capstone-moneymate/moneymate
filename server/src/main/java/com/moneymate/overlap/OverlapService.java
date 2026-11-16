package com.moneymate.overlap;

import com.moneymate.overlap.OverlapDtos.DirectionPair;
import com.moneymate.overlap.OverlapDtos.EtfChange;
import com.moneymate.overlap.OverlapDtos.FilerChange;
import com.moneymate.overlap.OverlapDtos.OverlapList;
import com.moneymate.overlap.OverlapDtos.StockOverlap;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

/**
 * 탭2 겹침 목록과 종목 상세 (A, 5~6주차).
 *
 * overlap_results 를 가장 최근 계산일(calc_date) 기준으로 읽어 종목별로 묶기만 한다.
 * 겹침·방향·"몇 명 늘림"은 서버가 다시 계산하지 않는다 (worker/compute/overlap.py 가 정답).
 */
@Service
public class OverlapService {

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

    public StockOverlap stock(String ticker) {
        String normalized = normalizeTicker(ticker);
        LocalDate calcDate = repository.findLatestCalcDate().orElseThrow(() -> new StockNotFound(normalized));
        List<StockOverlap> stocks = group(repository.findRows(calcDate, normalized));
        if (stocks.isEmpty()) {
            throw new StockNotFound(normalized);
        }
        return stocks.get(0);
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
