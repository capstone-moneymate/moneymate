package com.moneymate.news;

import java.math.BigDecimal;
import java.time.LocalDate;

/** prices 일봉 한 줄. open·high·low 는 비어 있을 수 있다(그때는 close 로 채운다). */
public record CandleRow(LocalDate marketDate, BigDecimal open, BigDecimal high, BigDecimal low, BigDecimal close) {
}
