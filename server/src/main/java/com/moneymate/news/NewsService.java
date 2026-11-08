package com.moneymate.news;

import com.moneymate.news.NewsDtos.CardDetail;
import com.moneymate.news.NewsDtos.MarketIndex;
import com.moneymate.news.NewsDtos.NewsCardSummary;
import com.moneymate.news.NewsDtos.NewsHome;
import java.math.BigDecimal;
import java.math.MathContext;
import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

/**
 * 탭1 뉴스 홈과 카드 상세 (C, 4주차).
 *
 * DB 의 snake_case JSON(cards.slides, steps.content)을 web 타입에 맞게 camelCase 로 바꾼다.
 * 정답(steps.answer)은 SQL 에서 읽지 않고, content 에 정답 키가 섞여 들어와도 여기서 한 번 더 지운다.
 * 카드 상태: 기본은 published 만 (conventions P8). NEWS_INCLUDE_PENDING=true 면 pending 도 보여 준다(데모·검수용).
 */
@Service
public class NewsService {

    private static final Logger log = LoggerFactory.getLogger(NewsService.class);
    static final ZoneId KST = ZoneId.of("Asia/Seoul");

    /** 홈 상단 지수 4개 (worker/collectors/prices.py INDEXES 와 같은 키·이름), 화면 순서대로 */
    static final Map<String, String> INDICES = indexNames();

    /** 홈 카드 한 줄 요약 최대 글자 수 (첫 슬라이드 본문을 자른다) */
    static final int SUMMARY_MAX = 80;

    /** content 에 있으면 안 되는 정답 키. compose.py 는 정답을 steps.answer 에만 쓰지만 한 번 더 막는다 */
    static final Set<String> ANSWER_KEYS = Set.of("answer", "answer_index", "answer_order", "correct",
            "explanation", "chart_check", "check", "causal", "chain", "counter", "change", "direction",
            "evidence_quote");

    private final NewsRepository repository;
    private final boolean includePending;
    private final Clock clock;
    private final JsonMapper json = JsonMapper.builder().build();

    @Autowired
    public NewsService(NewsRepository repository,
                       @Value("${NEWS_INCLUDE_PENDING:false}") boolean includePending) {
        this(repository, includePending, Clock.system(KST));
    }

    NewsService(NewsRepository repository, boolean includePending, Clock clock) {
        this.repository = repository;
        this.includePending = includePending;
        this.clock = clock;
    }

    public NewsHome home(String userId) {
        LocalDate today = LocalDate.now(clock.withZone(KST));
        LocalDate cardDate = repository.findLatestCardDate(today, includePending).orElse(today);
        List<CardRow> rows = repository.findCardsByDate(cardDate, includePending);

        List<NewsCardSummary> cards = rows.stream().map(this::summary).toList();
        List<String> completed = List.of();
        if (userId != null && !rows.isEmpty()) {
            List<Long> ids = rows.stream().map(CardRow::id).toList();
            completed = repository.findCompletedCardIds(userId, ids).stream().map(String::valueOf).toList();
        }
        return new NewsHome(cardDate.toString(), indices(repository.findLatestIndices(List.copyOf(INDICES.keySet()))),
                cards, completed);
    }

    public CardDetail card(long cardId) {
        CardRow c = repository.findCard(cardId, includePending).orElseThrow(() -> new CardNotFound(cardId));
        List<Map<String, Object>> steps = repository.findSteps(cardId).stream().map(this::step).toList();
        return new CardDetail(String.valueOf(c.id()), c.cardType(), c.title(), c.theme(), sourceName(c),
                c.sourceUrl(), sourcePublishedAt(c), c.ticker(), slides(c.slidesJson()), steps);
    }

    // --- 지수 ---

    List<MarketIndex> indices(List<IndexRow> rows) {
        Map<String, IndexRow> byTicker = new LinkedHashMap<>();
        rows.forEach(r -> byTicker.put(r.ticker(), r));
        List<MarketIndex> out = new ArrayList<>();
        INDICES.forEach((code, name) -> {
            IndexRow r = byTicker.get(code);
            if (r != null) {
                out.add(new MarketIndex(code, name, r.close().doubleValue(), chgPct(r.close(), r.prevClose()),
                        r.marketDate().toString()));
            }
        });
        return out;
    }

    /** (오늘 - 전날) / 전날. 전날이 없거나 0이면 null (conventions P2 와 같은 규칙). */
    static Double chgPct(BigDecimal close, BigDecimal prev) {
        if (prev == null || prev.signum() == 0) {
            return null;
        }
        return close.subtract(prev).divide(prev, MathContext.DECIMAL64).doubleValue();
    }

    // --- 카드 ---

    NewsCardSummary summary(CardRow c) {
        return new NewsCardSummary(String.valueOf(c.id()), c.cardType(), c.title(), summaryText(c.slidesJson()),
                c.theme(), sourceName(c), c.sourceUrl(), sourcePublishedAt(c), c.stepCount());
    }

    /** 첫 슬라이드("무슨 일이 있었나요?") 본문. SUMMARY_MAX 글자를 넘으면 자르고 … 를 붙인다. */
    String summaryText(String slidesJson) {
        List<Map<String, Object>> slides = slides(slidesJson);
        if (slides.isEmpty() || !(slides.get(0).get("body") instanceof String body)) {
            return "";
        }
        String text = body.strip();
        if (text.codePointCount(0, text.length()) <= SUMMARY_MAX) {
            return text;
        }
        return text.substring(0, text.offsetByCodePoints(0, SUMMARY_MAX)).strip() + "…";
    }

    /** 출처 이름: 거시 발표는 기관 이름(예: 한국은행), 공시는 "DART · SK하이닉스" 처럼. */
    static String sourceName(CardRow c) {
        String issuer = c.issuerName();
        String label = c.sourceType() == null ? null : switch (c.sourceType()) {
            case "dart" -> "DART";
            case "sec_8k" -> "SEC 8-K";
            default -> null;   // macro 는 발표 기관 이름만
        };
        if (label == null) {
            return issuer == null ? "" : issuer;
        }
        return issuer == null || issuer.isBlank() ? label : label + " · " + issuer;
    }

    /** 1차 자료 발표 시각 (ISO, UTC). 시각을 모르면(DART) 그 날짜 0시 KST 로 둔다. 자료가 없으면 null. */
    static String sourcePublishedAt(CardRow c) {
        if (c.sourcePublishedAt() != null) {
            return c.sourcePublishedAt().withOffsetSameInstant(ZoneOffset.UTC).format(DateTimeFormatter.ISO_INSTANT);
        }
        if (c.sourcePublishedDate() != null) {
            return c.sourcePublishedDate().atStartOfDay(KST).toInstant().toString();
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    List<Map<String, Object>> slides(String slidesJson) {
        Object parsed = parse(slidesJson);
        if (!(parsed instanceof List<?> list)) {
            return List.of();
        }
        List<Map<String, Object>> out = new ArrayList<>();
        for (Object o : list) {
            if (camel(o) instanceof Map<?, ?> m) {
                out.add((Map<String, Object>) m);
            }
        }
        return out;
    }

    /** 단계 한 개: {id, no, kind} + content(정답 키 제외, camelCase). */
    Map<String, Object> step(StepRow s) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", String.valueOf(s.id()));
        out.put("no", s.stepNo());
        out.put("kind", s.kind());
        if (parse(s.contentJson()) instanceof Map<?, ?> content) {
            content.forEach((k, v) -> {
                String key = String.valueOf(k);
                if (!ANSWER_KEYS.contains(key) && !out.containsKey(toCamel(key))) {
                    out.put(toCamel(key), camel(v));
                }
            });
        }
        out.putIfAbsent("conceptIds", List.of());
        return out;
    }

    private Object parse(String jsonText) {
        if (jsonText == null || jsonText.isBlank()) {
            return null;
        }
        try {
            return json.readValue(jsonText, Object.class);
        } catch (JacksonException e) {
            log.warn("카드 JSON 을 읽지 못했어요: {}", e.getOriginalMessage());
            return null;
        }
    }

    /** JSON 값(Map/List/값)의 모든 키를 camelCase 로 바꾼다. 값(문자열)은 그대로 둔다. */
    static Object camel(Object value) {
        if (value instanceof Map<?, ?> m) {
            Map<String, Object> out = new LinkedHashMap<>();
            m.forEach((k, v) -> out.put(toCamel(String.valueOf(k)), camel(v)));
            return out;
        }
        if (value instanceof List<?> list) {
            return list.stream().map(NewsService::camel).toList();
        }
        return value;
    }

    /** concept_ids → conceptIds, start_date → startDate. 이미 camelCase 면 그대로. */
    static String toCamel(String key) {
        StringBuilder sb = new StringBuilder(key.length());
        boolean upper = false;
        for (char ch : key.toCharArray()) {
            if (ch == '_') {
                upper = sb.length() > 0;
            } else {
                sb.append(upper ? Character.toUpperCase(ch) : ch);
                upper = false;
            }
        }
        return sb.toString();
    }

    private static Map<String, String> indexNames() {
        Map<String, String> m = new LinkedHashMap<>();
        m.put("KS11", "KOSPI");
        m.put("KQ11", "KOSDAQ");
        m.put("IXIC", "NASDAQ");
        m.put("US500", "S&P 500");
        return m;
    }

    /** 없는 카드이거나 보여 줄 상태(published, 설정 시 pending)가 아니다 → 404. */
    public static class CardNotFound extends RuntimeException {
        public CardNotFound(long cardId) {
            super("카드를 찾을 수 없어요: " + cardId);
        }
    }
}
