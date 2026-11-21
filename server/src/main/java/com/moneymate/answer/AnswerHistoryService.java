package com.moneymate.answer;

import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

/**
 * 탭3 "풀었던 내용 보기" (C). 한 카드에서 내가 낸 답과 채점 결과를 단계별로 돌려준다. DB 읽기만 한다.
 * 날짜(KST)를 주면 그날 마지막 답안, 안 주면 단계마다 가장 최근 답안.
 * 정답·해설은 그 단계에 답을 낸 적이 있을 때만 내려간다 (답을 낼 때 POST /api/answers 가 이미 보여 준 값).
 */
@Service
public class AnswerHistoryService {

    private final AnswerHistoryRepository repository;
    private final JsonMapper json = JsonMapper.builder().build();

    public AnswerHistoryService(AnswerHistoryRepository repository) {
        this.repository = repository;
    }

    public List<PastAnswer> history(String userId, long cardId, LocalDate date) {
        return repository.findPastAnswers(userId, cardId, date).stream().map(this::toPast).toList();
    }

    PastAnswer toPast(PastAnswerRow r) {
        String stepId = String.valueOf(r.stepId());
        Map<String, Object> saved = readMap(r.answerJson());
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("kind", r.kind());
        if ("judgement".equals(r.kind())) {
            input.put("choice", saved.get("choice"));
            input.put("reason", saved.get("text"));
            return new PastAnswer(stepId, input,
                    new PastAnswer.Result(stepId, r.isCorrect(), null, null, grade(r)));
        }
        if ("causal_order".equals(r.kind())) {
            input.put("order", saved.get("order"));
        } else {
            input.put("optionIndex", saved.get("option_index"));
        }
        Map<String, Object> key = readMap(r.keyJson());
        String explanation = key.get("explanation") instanceof String s ? s : null;
        return new PastAnswer(stepId, input,
                new PastAnswer.Result(stepId, r.isCorrect(), explanation, key.get("correct"), null));
    }

    /** 저장된 판단 채점을 /api/judgement 응답(JudgementGrade) 모양으로. 점수가 없으면 채점 못 한 답안 */
    private Map<String, Object> grade(PastAnswerRow r) {
        Map<String, Object> stored = readMap(r.feedbackJson());
        Map<String, Object> g = new LinkedHashMap<>();
        g.put("score", r.score());
        g.put("correct", r.isCorrect());
        g.put("rubric", r.rubricJson() == null ? null : readMap(r.rubricJson()));
        g.put("reasons", stored.get("reasons") instanceof Map<?, ?> m ? m : Map.of());
        g.put("grader", "llm".equals(r.gradedBy()) ? "claude" : "rule".equals(r.gradedBy()) ? "rule" : null);
        g.put("reused", false);
        g.put("message", r.score() == null ? "이 답안은 채점하지 못했어요." : null);
        g.put("feedback", stored.get("feedback"));
        return g;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readMap(String text) {
        if (text == null || text.isBlank()) {
            return Map.of();
        }
        try {
            return json.readValue(text, Object.class) instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of();
        } catch (JacksonException e) {
            return Map.of();
        }
    }
}
