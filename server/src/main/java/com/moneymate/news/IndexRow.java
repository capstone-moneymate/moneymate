package com.moneymate.news;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * prices 에서 읽은 지수 한 줄.
 *
 * @param ticker     KS11 / KQ11 / IXIC / US500
 * @param marketDate 가장 최근 거래일 (그 시장 날짜)
 * @param close      그날 종가
 * @param prevClose  그 전 거래일 종가 (없으면 null)
 */
public record IndexRow(String ticker, LocalDate marketDate, BigDecimal close, BigDecimal prevClose) {
}
