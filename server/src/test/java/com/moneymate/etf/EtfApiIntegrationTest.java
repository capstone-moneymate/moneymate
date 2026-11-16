package com.moneymate.etf;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.moneymate.TestDatabase;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.json.JsonCompareMode;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

/** ETF 어제 변화 API 통합 테스트. fixtures/etf_daily.sql 의 손계산이 정답이다. Docker 가 없으면 건너뛴다. */
@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers(disabledWithoutDocker = true)
class EtfApiIntegrationTest {

    @Container
    @ServiceConnection
    static final PostgreSQLContainer POSTGRES = TestDatabase.postgres("fixtures/etf_daily.sql");

    @Autowired
    MockMvc mvc;

    @Test
    void dailySplitsLatestSnapshotIntoThreeCards() throws Exception {
        String expected = """
                {"threshold":0.05,
                 "etfs":[{"etfCode":"0015B0","snapshotDate":"2026-11-13"},
                         {"etfCode":"426030","snapshotDate":"2026-11-13"}],
                 "together":[{"ticker":"NVDA","rawCode":"7066G1","stockName":"NVIDIA CORP","moves":[
                     {"etfCode":"0015B0","ticker":"NVDA","rawCode":"7066G1","stockName":"NVIDIA CORP","dayChgPct":0.08},
                     {"etfCode":"426030","ticker":null,"rawCode":"7066G1","stockName":"NVIDIA CORP","dayChgPct":0.06}]}],
                 "topIncrease":[
                     {"etfCode":"0015B0","ticker":"AMZN","rawCode":"023135","stockName":"AMAZON.COM INC","dayChgPct":0.2},
                     {"etfCode":"0015B0","ticker":"NVDA","rawCode":"7066G1","stockName":"NVIDIA CORP","dayChgPct":0.08},
                     {"etfCode":"426030","ticker":null,"rawCode":"7066G1","stockName":"NVIDIA CORP","dayChgPct":0.06}],
                 "topDecrease":[
                     {"etfCode":"426030","ticker":"MSFT","rawCode":"594918","stockName":"MICROSOFT CORP","dayChgPct":-0.3},
                     {"etfCode":"0015B0","ticker":"AAPL","rawCode":"037833","stockName":"APPLE INC","dayChgPct":-0.1},
                     {"etfCode":"426030","ticker":"META","rawCode":"30303M","stockName":"META PLATFORMS INC","dayChgPct":-0.06}]}""";

        mvc.perform(get("/api/etf/daily"))
                .andExpect(status().isOk())
                .andExpect(content().json(expected, JsonCompareMode.STRICT));
    }
}
