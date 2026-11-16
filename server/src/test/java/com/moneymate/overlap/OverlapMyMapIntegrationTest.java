package com.moneymate.overlap;

import static org.assertj.core.api.Assertions.assertThat;

import com.moneymate.TestDatabase;
import com.moneymate.overlap.OverlapDtos.MyMapConcept;
import com.moneymate.overlap.OverlapDtos.MyMapTicker;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

/**
 * "내 지도에 있어요" 쿼리 (#100). 빈 PostgreSQL 16 에 마이그레이션(005 concept_tickers 포함)과
 * fixtures/my_map.sql 을 넣고 실제 SQL 을 확인한다. 손계산은 fixture 맨 위. Docker 가 없으면 건너뛴다.
 */
@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class OverlapMyMapIntegrationTest {

    static final String USER = "11111111-1111-1111-1111-111111111111";
    static final MyMapConcept GPU = new MyMapConcept("gpu_demand", "AI 반도체 수요", "AI·반도체");

    @Container
    @ServiceConnection
    static final PostgreSQLContainer POSTGRES = TestDatabase.postgres("fixtures/my_map.sql");

    @Autowired
    OverlapService service;

    @Test
    void tickersLinkedToLearnedConcepts() {
        // semi_earnings 는 total 0 이라 NVDA 에 붙지 않고, rate_hike 는 연결된 종목이 없다
        assertThat(service.myMapTickers(USER)).containsExactly(
                new MyMapTicker("AMD", List.of(GPU)),
                new MyMapTicker("NVDA", List.of(GPU)));
    }

    @Test
    void learnedConceptsOfOneTicker() {
        assertThat(service.myConceptsForTicker(USER, " nvda ")).containsExactly(GPU);
        assertThat(service.myConceptsForTicker(USER, "GOOGL")).isEmpty();   // ai_investment 는 안 배움
    }

    @Test
    void otherUserSeesOnlyTheirOwnMap() {
        assertThat(service.myMapTickers("22222222-2222-2222-2222-222222222222")).containsExactly(
                new MyMapTicker("GOOGL", List.of(new MyMapConcept("ai_investment", "AI 데이터센터 투자", "AI·반도체"))));
        assertThat(service.myMapTickers("33333333-3333-3333-3333-333333333333")).isEmpty();   // 처음 보는 사용자
    }
}
