package com.moneymate.etf;

import com.moneymate.etf.EtfDtos.EtfDaily;
import com.moneymate.etf.EtfDtos.EtfMove;
import com.moneymate.etf.EtfDtos.EtfSnapshot;
import com.moneymate.etf.EtfDtos.TogetherMove;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * 탭2 액티브 ETF "어제 매니저들이 움직인 종목" (A, #98).
 *
 * holdings_etf.day_chg_pct(B 의 etf_trend.py 값)를 그대로 읽고, 화면 카드 세 가지로 나누기만 한다.
 * - 늘림: day_chg_pct >= threshold, 줄임: day_chg_pct <= -threshold
 * - together: 최신 스냅샷이 있는 모든 ETF(2개 이상)가 같은 종목(raw_code)을 늘림
 * - topIncrease / topDecrease: 늘림·줄임 중 변화율이 큰 (ETF, 종목) 최대 TOP_N 개
 * 기준값은 worker/config.py ETF_TREND_THRESHOLD 와 같은 0.05 를 기본으로 쓴다. 하나를 바꾸면 둘 다 바꾼다.
 */
@Service
public class EtfService {

    static final int TOP_N = 3;

    private final EtfRepository repository;
    private final BigDecimal threshold;

    @Autowired
    public EtfService(EtfRepository repository, @Value("${ETF_DAY_THRESHOLD:0.05}") BigDecimal threshold) {
        this.repository = repository;
        this.threshold = threshold;
    }

    public EtfDaily daily() {
        List<EtfSnapshot> etfs = repository.findLatestSnapshots().stream()
                .map(r -> new EtfSnapshot(r.etfCode(), r.snapshotDate().toString()))
                .toList();
        List<EtfRow> moves = repository.findLatestMoves();

        List<EtfRow> ups = moves.stream().filter(this::isUp).toList();
        List<EtfRow> downs = moves.stream().filter(this::isDown).toList();

        List<EtfMove> topIncrease = ups.stream()
                .sorted(Comparator.comparing(EtfRow::dayChgPct).reversed().thenComparing(EtfService::tieBreak))
                .limit(TOP_N).map(EtfService::move).toList();
        List<EtfMove> topDecrease = downs.stream()
                .sorted(Comparator.comparing(EtfRow::dayChgPct).thenComparing(EtfService::tieBreak))
                .limit(TOP_N).map(EtfService::move).toList();

        return new EtfDaily(threshold.doubleValue(), etfs, together(ups, etfs.size()), topIncrease, topDecrease);
    }

    /** 모든 ETF 가 늘린 종목. ETF 가 하나뿐이면 "함께"가 아니므로 빈 목록. */
    static List<TogetherMove> together(List<EtfRow> ups, int etfCount) {
        if (etfCount < 2) {
            return List.of();
        }
        Map<String, List<EtfRow>> byCode = new LinkedHashMap<>();
        for (EtfRow r : ups) {
            byCode.computeIfAbsent(r.rawCode(), k -> new ArrayList<>()).add(r);
        }
        List<TogetherMove> out = new ArrayList<>();
        byCode.forEach((rawCode, rows) -> {
            if (rows.size() == etfCount) {
                EtfRow first = rows.get(0);
                String ticker = rows.stream().map(EtfRow::ticker).filter(t -> t != null).findFirst().orElse(null);
                out.add(new TogetherMove(ticker, rawCode, first.stockName(), rows.stream().map(EtfService::move).toList()));
            }
        });
        return out;
    }

    private boolean isUp(EtfRow r) {
        return r.dayChgPct().compareTo(threshold) >= 0;
    }

    private boolean isDown(EtfRow r) {
        return r.dayChgPct().compareTo(threshold.negate()) <= 0;
    }

    private static String tieBreak(EtfRow r) {
        return r.etfCode() + "/" + r.rawCode();
    }

    private static EtfMove move(EtfRow r) {
        return new EtfMove(r.etfCode(), r.ticker(), r.rawCode(), r.stockName(), r.dayChgPct().doubleValue());
    }
}
