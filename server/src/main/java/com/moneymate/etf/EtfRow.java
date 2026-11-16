package com.moneymate.etf;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * ETF 별 최신 스냅샷의 구성종목 한 줄 (holdings_etf 값 그대로).
 *
 * @param etfCode      holdings_etf.etf_code
 * @param snapshotDate holdings_etf.snapshot_date (그 ETF 의 가장 최근 스냅샷)
 * @param rawCode      holdings_etf.raw_code (CUSIP 2~7번째 글자, 두 ETF 를 맞출 때 쓴다)
 * @param ticker       holdings_etf.ticker (변환 못 했으면 null)
 * @param stockName    holdings_etf.stock_name
 * @param dayChgPct    holdings_etf.day_chg_pct (전 거래일 대비, 소수)
 */
public record EtfRow(
        String etfCode,
        LocalDate snapshotDate,
        String rawCode,
        String ticker,
        String stockName,
        BigDecimal dayChgPct) {
}
