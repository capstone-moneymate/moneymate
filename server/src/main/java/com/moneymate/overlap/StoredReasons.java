package com.moneymate.overlap;

import java.util.List;
import java.util.Map;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.json.JsonMapper;

/**
 * stock_reasons 의 JSON 칸을 읽는 모양 (C 의 docs/modules/reasons.md "저장 모양", snake_case).
 * 서버는 이 값을 계산하지 않고 화면용 DTO(OverlapDtos)로 옮기기만 한다. 모르는 키는 무시한다.
 */
final class StoredReasons {

    private StoredReasons() {
    }

    static final JsonMapper JSON = JsonMapper.builder()
            .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .build();

    /** 카드 ② 이유 하나. path 는 B 의 사전 경로(개념 id), direction 은 up/down. */
    record Reason(String title, String body, String startConcept, String endConcept, List<String> path,
                  String direction, List<Evidence> evidence) {
    }

    /** 근거 자료. no 는 이유를 만들 때 근거 후보에 붙인 번호, sourceId 는 raw_sources.id. */
    record Evidence(Integer no, Long sourceId, String publishedDate, String title, String issuerName, String url) {
    }

    /** 카드 ③ 지금은 (stock_now.StockNow.to_json()). errors 는 화면에 내보내지 않는다. */
    record NowView(String baseDate, Price price, List<LaterSource> laterSources, List<Linked> linked, String text,
                   List<String> errors) {
    }

    /** returnPct 는 C 가 퍼센트 값으로 저장한다 (12.5 = 12.5%). */
    record Price(String fromDate, Double fromClose, String toDate, Double toClose, Double returnPct) {
    }

    record LaterSource(Long sourceId, String publishedDate, String title, String url, Map<String, Object> numbers) {
    }

    record Linked(String conceptId, String name, String reasonTitle) {
    }

    static List<Reason> readReasons(String json) {
        return List.of(JSON.readValue(json, Reason[].class));
    }

    static NowView readNowView(String json) {
        return json == null || json.isBlank() ? null : JSON.readValue(json, NowView.class);
    }
}
