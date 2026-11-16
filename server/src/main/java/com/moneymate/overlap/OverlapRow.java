package com.moneymate.overlap;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * overlap_results 한 줄 + 같은 큰손·분기의 holdings_13f 값 + 같은 ETF·스냅샷의 holdings_etf 값.
 * 붙인 값은 DB 에 저장된 그대로이고 서버가 계산한 값은 없다.
 *
 * @param calcDate        overlap_results.calc_date
 * @param ticker          overlap_results.ticker
 * @param filerKey        overlap_results.filer_key (buffett / druckenmiller / thiel / ackman)
 * @param bigPeriodEnd    overlap_results.big_period_end (사용한 13F 분기 말)
 * @param bigChgPct       overlap_results.big_chg_pct (소수, 신규 편입이면 null)
 * @param etfCode         overlap_results.etf_code
 * @param etfSnapshotDate overlap_results.etf_snapshot_date (비교에 쓴 ETF 최신 스냅샷)
 * @param etfTrendChgPct  overlap_results.etf_trend_chg_pct (소수, ETF 신규 편입이면 null)
 * @param direction       overlap_results.direction (same / diff / none)
 * @param filerName       holdings_13f.filer_name (제출 법인명)
 * @param issuerName      holdings_13f.issuer_name
 * @param changeType      holdings_13f.change_type (new / increase / decrease / exit / unchanged)
 * @param filedAt         holdings_13f.filed_at (공시일)
 * @param etfStockName    holdings_etf.stock_name (최신 스냅샷에 없으면 null)
 * @param etfDayChgPct    holdings_etf.day_chg_pct (최신 스냅샷의 전 거래일 대비, 없으면 null)
 */
public record OverlapRow(
        LocalDate calcDate,
        String ticker,
        String filerKey,
        LocalDate bigPeriodEnd,
        BigDecimal bigChgPct,
        String etfCode,
        LocalDate etfSnapshotDate,
        BigDecimal etfTrendChgPct,
        String direction,
        String filerName,
        String issuerName,
        String changeType,
        LocalDate filedAt,
        String etfStockName,
        BigDecimal etfDayChgPct) {
}
