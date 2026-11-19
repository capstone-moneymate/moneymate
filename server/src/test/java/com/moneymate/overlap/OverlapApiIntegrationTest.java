package com.moneymate.overlap;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;
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
import org.testcontainers.utility.MountableFile;

/**
 * 겹침 API 통합 테스트. 빈 PostgreSQL 16 에 db/migrations(001~)와 fixtures/overlap.sql 을 넣고
 * 실제 SQL·MyBatis 매핑·JSON 응답을 확인한다. Docker 가 없으면 건너뛴다.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers(disabledWithoutDocker = true)
class OverlapApiIntegrationTest {

    /** gradle 테스트는 server/ 에서 돈다 */
    static final Path MIGRATIONS = Path.of("..", "db", "migrations");

    @Container
    @ServiceConnection
    static final PostgreSQLContainer POSTGRES = withInitScripts(new PostgreSQLContainer("postgres:16"));

    /** 빈 DB 가 처음 뜰 때 /docker-entrypoint-initdb.d 의 파일이 이름 순서로 실행된다 (docker-compose.yml 과 같은 방식). */
    static PostgreSQLContainer withInitScripts(PostgreSQLContainer c) {
        try (Stream<Path> files = Files.list(MIGRATIONS)) {
            files.filter(p -> p.toString().endsWith(".sql")).forEach(p -> c.withCopyFileToContainer(
                    MountableFile.forHostPath(p), "/docker-entrypoint-initdb.d/" + p.getFileName()));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return c.withCopyFileToContainer(MountableFile.forClasspathResource("fixtures/overlap.sql"),
                "/docker-entrypoint-initdb.d/900_overlap_fixture.sql");
    }

    static final String NVDA = """
            {"calcDate":"2026-11-14","ticker":"NVDA","issuerName":"NVIDIA CORPORATION","etfStockName":"NVIDIA CORP",
             "filers":[
               {"filerKey":"druckenmiller","filerName":"Duquesne Family Office LLC","changeType":"increase",
                "chgPct":0.1,"periodEnd":"2026-06-30","filedAt":"2026-08-14"},
               {"filerKey":"thiel","filerName":"Thiel Macro LLC","changeType":"new",
                "chgPct":null,"periodEnd":"2026-06-30","filedAt":"2026-08-13"}],
             "etfs":[
               {"etfCode":"0015B0","snapshotDate":"2026-11-13","trendChgPct":0.05,"dayChgPct":0.01},
               {"etfCode":"426030","snapshotDate":"2026-11-13","trendChgPct":-0.16318,"dayChgPct":-0.02}],
             "pairs":[
               {"filerKey":"druckenmiller","etfCode":"0015B0","direction":"same"},
               {"filerKey":"druckenmiller","etfCode":"426030","direction":"diff"},
               {"filerKey":"thiel","etfCode":"0015B0","direction":"same"},
               {"filerKey":"thiel","etfCode":"426030","direction":"diff"}]""";

    static final String USER = "11111111-1111-1111-1111-111111111111";

    /** 카드 ②③ (fixture 의 2026-06-30 published). learned 자리는 사용자에 따라 바꿔 끼운다 */
    static String nvdaReasons(boolean learned) {
        return """
            "reasons":{"bigPeriodEnd":"2026-06-30","direction":"diff","change":"up","headline":"왜 방향이 다를까요?",
             "reasons":[{"title":"AI 투자 확대","body":"데이터센터 투자가 늘어 GPU 수요가 커졌을 수 있어요.",
               "path":[{"id":"ai_investment","name":"AI 데이터센터 투자","learned":false},
                       {"id":"gpu_demand","name":"AI 반도체 수요","learned":%s},
                       {"id":"semi_earnings","name":"반도체 기업 실적","learned":false}],
               "direction":"up","inMyMap":%s,
               "evidence":[{"no":4,"publishedDate":"2026-06-12","title":"데이터센터 투자 발표",
                            "issuerName":"Microsoft","url":"https://example.com/a"}],
               "side":null}],
             "now":{"baseDate":"2026-06-30",
               "price":{"fromDate":"2026-06-30","fromClose":100.0,"toDate":"2026-11-14","toClose":112.5,"returnPct":12.5},
               "laterSources":[],"linked":[],"text":null}}""".formatted(learned, learned);
    }

    static final String GOOGL = """
            {"calcDate":"2026-11-14","ticker":"GOOGL","issuerName":"ALPHABET INC","etfStockName":"ALPHABET INC-CL A",
             "filers":[
               {"filerKey":"ackman","filerName":"Pershing Square Inc.","changeType":"decrease",
                "chgPct":-0.25,"periodEnd":"2026-06-30","filedAt":"2026-08-14"}],
             "etfs":[{"etfCode":"0015B0","snapshotDate":"2026-11-13","trendChgPct":0.1,"dayChgPct":0.0}],
             "pairs":[{"filerKey":"ackman","etfCode":"0015B0","direction":"diff"}]""";

    @Autowired
    MockMvc mvc;

    @Test
    void listReturnsLatestCalcDateGroupedByTicker() throws Exception {
        // 2026-11-13 행(direction none)은 빠지고, AAPL 은 ETF 가 없어 겹침 행이 없으므로 안 나온다
        mvc.perform(get("/api/overlaps"))
                .andExpect(status().isOk())
                .andExpect(content().json("{\"calcDate\":\"2026-11-14\",\"stocks\":[" + GOOGL + "}," + NVDA + "}]}",
                        JsonCompareMode.STRICT));
    }

    @Test
    void stockDetailByTickerPathVariable() throws Exception {
        // 426030 최신 스냅샷은 holdings_etf.ticker 가 NULL 이어도 raw_code(CUSIP 2~7번째)로 어제 변화를 찾는다
        // 카드 ②③ 은 published 중 가장 최근 분기(2026-06-30). 더 최근 pending 과 오래된 published 는 빠진다.
        // userId 가 없으면 배운 개념 표시가 없다. 카드 ③ 의 errors 는 내보내지 않는다
        mvc.perform(get("/api/stocks/NVDA"))
                .andExpect(status().isOk())
                .andExpect(content().json(NVDA + "," + nvdaReasons(false) + ",\"reasonsRejected\":false,\"myConcepts\":[]}",
                        JsonCompareMode.STRICT));
    }

    @Test
    void stockDetailWithUserShowsMyMap() throws Exception {
        // 사용자가 gpu_demand 를 배워서: 이유 경로의 그 개념이 learned, 이유는 inMyMap,
        // concept_tickers(gpu_demand -> NVDA)로 myConcepts 에 들어간다
        mvc.perform(get("/api/stocks/NVDA").param("userId", USER))
                .andExpect(status().isOk())
                .andExpect(content().json(NVDA + "," + nvdaReasons(true)
                        + ",\"reasonsRejected\":false,\"myConcepts\":[{\"id\":\"gpu_demand\",\"name\":\"AI 반도체 수요\",\"theme\":\"AI·반도체\"}]}",
                        JsonCompareMode.STRICT));
    }

    @Test
    void invalidUserIdIs400() throws Exception {
        mvc.perform(get("/api/stocks/NVDA").param("userId", "abc"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void stockDetailNormalizesLowercaseTicker() throws Exception {
        // GOOGL 은 rejected 만 있어 reasons 가 null 이고 reasonsRejected 가 true (화면은 "이유를 찾지 못했어요" 고정 문구, #164)
        mvc.perform(get("/api/stocks/googl").param("userId", USER))
                .andExpect(status().isOk())
                .andExpect(content().json(GOOGL + ",\"reasons\":null,\"reasonsRejected\":true,\"myConcepts\":[]}",
                        JsonCompareMode.STRICT));
    }

    @Test
    void stockWithoutOverlapIs404() throws Exception {
        mvc.perform(get("/api/stocks/AAPL"))
                .andExpect(status().isNotFound())
                .andExpect(content().json("{\"message\":\"겹침 결과에 없는 종목입니다: AAPL\"}", JsonCompareMode.STRICT));
    }
}
