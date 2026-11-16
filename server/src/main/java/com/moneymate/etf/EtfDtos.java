package com.moneymate.etf;

import java.util.List;

/** 탭2 액티브 ETF "어제 움직인 종목" API 응답. 변화율은 소수(0.05 = +5%), 날짜는 YYYY-MM-DD. */
public final class EtfDtos {

    private EtfDtos() {
    }

    /** ETF 하나와 그 ETF 의 가장 최근 스냅샷 날짜. */
    public record EtfSnapshot(String etfCode, String snapshotDate) {
    }

    /** ETF 하나에서 종목 하나의 어제 변화. */
    public record EtfMove(String etfCode, String ticker, String rawCode, String stockName, double dayChgPct) {
    }

    /** 모든 ETF 가 함께 늘린 종목. moves 는 ETF 코드 순. */
    public record TogetherMove(String ticker, String rawCode, String stockName, List<EtfMove> moves) {
    }

    /** GET /api/etf/daily. 스냅샷이 하나도 없으면 etfs·목록이 모두 빈 값이다. */
    public record EtfDaily(
            double threshold,
            List<EtfSnapshot> etfs,
            List<TogetherMove> together,
            List<EtfMove> topIncrease,
            List<EtfMove> topDecrease) {
    }
}
