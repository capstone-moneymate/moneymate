package com.moneymate.answer;

import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

/**
 * 탭1 코드 채점 (C, 4주차): 간단 퀴즈·차트 읽기(보기 번호), 인과 순서(개념 id 순서).
 *
 * 순서: 단계 확인 → kind·입력 확인 → steps.answer 의 정답과 비교 → user_answers 저장(graded_by='code') → 결과·해설·정답.
 * 정답은 compose.py 가 출제 때 코드로 확인해 steps.answer 에 넣은 값이다. 여기서는 비교만 한다.
 * 판단해보기는 루브릭 채점이라 A의 POST /api/judgement 로 보낸다.
 */
@Service
public class AnswerService {

    private static final Logger log = LoggerFactory.getLogger(AnswerService.class);

    private final AnswerRepository repository;
    private final boolean includePending;
    private final JsonMapper json = JsonMapper.builder().build();

    public AnswerService(AnswerRepository repository,
                         @Value("${NEWS_INCLUDE_PENDING:false}") boolean includePending) {
        this.repository = repository;
        this.includePending = includePending;
    }

    @Transactional
    public AnswerResult submit(AnswerRequest req) {
        AnswerStep step = repository.findStep(req.stepId(), includePending)
                .orElseThrow(() -> new AnswerExceptions.StepNotFound(req.stepId()));
        AnswerRequest.Input in = req.answer();
        if ("judgement".equals(step.kind())) {
            throw new AnswerExceptions.BadAnswer("판단해보기는 /api/judgement 로 보내 주세요.");
        }
        if (!step.kind().equals(in.kind())) {
            throw new AnswerExceptions.BadAnswer(
                    "이 단계는 " + step.kind() + " 인데 " + in.kind() + " 답이 왔어요.");
        }
        Map<String, Object> key = readKey(step);

        boolean correct;
        Object correctValue;
        Map<String, Object> saved = new LinkedHashMap<>();
        saved.put("kind", in.kind());
        switch (step.kind()) {
            case "quiz", "chart" -> {
                Integer chosen = in.optionIndex();
                if (chosen == null || chosen < 0 || chosen >= step.optionCount()) {
                    throw new AnswerExceptions.BadAnswer(
                            "보기 번호는 0부터 " + (step.optionCount() - 1) + " 사이여야 해요.");
                }
                if (!(key.get("correct") instanceof Number n)) {
                    throw brokenKey(step);
                }
                correctValue = n.intValue();
                correct = chosen == n.intValue();
                saved.put("option_index", chosen);
            }
            case "causal_order" -> {
                List<String> order = in.order();
                List<String> answer = stringList(key.get("correct"));
                if (answer == null) {
                    throw brokenKey(step);
                }
                // 화면이 섞어 준 개념을 빠짐없이 한 번씩 놓았는지 (다른 개념·빠뜨림·중복이면 400)
                if (order == null || order.size() != answer.size()
                        || !new HashSet<>(order).equals(new HashSet<>(answer))
                        || new HashSet<>(order).size() != order.size()) {
                    throw new AnswerExceptions.BadAnswer("순서에는 이 단계의 개념을 한 번씩 모두 넣어 주세요.");
                }
                correctValue = answer;
                correct = order.equals(answer);
                saved.put("order", order);
            }
            default -> throw new AnswerExceptions.BadAnswer("채점하지 않는 단계예요: " + step.kind());
        }

        String userId = req.userId().toString();
        repository.ensureUser(userId);
        repository.insertAnswer(userId, step.cardId(), step.stepId(), json.writeValueAsString(saved), correct);
        // TODO(P17): B의 recordConceptResult(userId, step.conceptIds(), correct) 가 생기면 여기서 부른다
        String explanation = key.get("explanation") instanceof String s ? s : null;
        return new AnswerResult(String.valueOf(step.stepId()), correct, explanation, correctValue);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> readKey(AnswerStep step) {
        if (step.answerJson() == null || step.answerJson().isBlank()) {
            throw brokenKey(step);
        }
        try {
            if (json.readValue(step.answerJson(), Object.class) instanceof Map<?, ?> m) {
                return (Map<String, Object>) m;
            }
        } catch (JacksonException e) {
            log.warn("정답 JSON 을 읽지 못했어요 (stepId={}): {}", step.stepId(), e.getOriginalMessage());
        }
        throw brokenKey(step);
    }

    private static List<String> stringList(Object value) {
        if (!(value instanceof List<?> list) || !list.stream().allMatch(String.class::isInstance)) {
            return null;
        }
        return list.stream().map(String.class::cast).toList();
    }

    private static AnswerExceptions.AnswerKeyMissing brokenKey(AnswerStep step) {
        log.error("정답이 없거나 형식이 달라요 (stepId={}, kind={})", step.stepId(), step.kind());
        return new AnswerExceptions.AnswerKeyMissing(step.stepId());
    }
}
