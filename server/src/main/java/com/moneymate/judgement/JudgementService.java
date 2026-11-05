package com.moneymate.judgement;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.Map;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

/**
 * 판단해보기 근거 채점 (A, #55) + AI 분석 피드백 (#56).
 *
 * 순서: 단계 확인 → 하루 호출 제한 → 같은 답안 해시 재사용 → FastAPI 채점 → user_answers 저장.
 * 채점·피드백 생성(루브릭·Claude·규칙 채점 전환)은 Python(worker/generate/judge.py)이 하고, 여기서는 다시 계산하지 않는다.
 * 피드백과 채점 이유는 user_answers.feedback(TEXT)에 JSON 문자열로 저장해, 재사용할 때 그대로 돌려준다.
 * FastAPI 호출이 실패하면 점수·피드백 없이 고정 문구를 돌려주고 답안은 저장한다.
 */
@Service
public class JudgementService {

    private static final Logger log = LoggerFactory.getLogger(JudgementService.class);
    static final ZoneId KST = ZoneId.of("Asia/Seoul");
    /** conventions P17: 60점 이상이면 맞음 */
    static final int CORRECT_SCORE = 60;
    /** 채점 서버 실패 시 문구 (기술확정안 "루브릭"의 고정 문구) */
    static final String FALLBACK_MESSAGE = "근거 있는 선택이었어요. 이런 경우도 생길 수 있어요.";

    /** user_answers.feedback 에 저장하는 모양. */
    record StoredFeedback(JudgementFeedback feedback, Map<String, String> reasons) {
    }

    private final JudgementRepository repository;
    private final JudgeClient judgeClient;
    private final JudgeProperties props;
    private final Clock clock;
    private final JsonMapper json = JsonMapper.builder().build();

    @Autowired
    public JudgementService(JudgementRepository repository, JudgeClient judgeClient, JudgeProperties props) {
        this(repository, judgeClient, props, Clock.system(KST));
    }

    JudgementService(JudgementRepository repository, JudgeClient judgeClient, JudgeProperties props, Clock clock) {
        this.repository = repository;
        this.judgeClient = judgeClient;
        this.props = props;
        this.clock = clock;
    }

    public JudgementResponse judge(JudgementRequest req) {
        String userId = req.userId().toString();
        JudgementStep step = repository.findStep(req.stepId())
                .orElseThrow(() -> new JudgementExceptions.StepNotFound(req.stepId()));

        int usedToday = repository.countJudgementsSince(userId, startOfTodayKst());
        if (usedToday >= props.dailyLimit()) {
            throw new JudgementExceptions.DailyLimitExceeded(props.dailyLimit());
        }

        repository.ensureUser(userId);
        String hash = AnswerHasher.hash(step.stepId(), req.answer());

        Optional<StoredGrade> reusable = repository.findReusable(step.stepId(), hash);
        if (reusable.isPresent()) {
            StoredGrade g = reusable.get();
            Rubric rubric = new Rubric(g.evidence(), g.reasoning(), g.rebuttal());
            boolean correct = g.score() >= CORRECT_SCORE;
            StoredFeedback stored = readFeedback(g.feedbackJson());
            save(userId, step, req, hash, correct, g.score(), rubric, g.gradedBy(), g.feedbackJson());
            return new JudgementResponse(g.score(), correct, rubric, stored.reasons(), "claude", true, null,
                    stored.feedback());
        }

        JudgeApiResponse result;
        try {
            result = judgeClient.judge(new JudgeApiRequest(
                    req.answer(), step.keyFactsJson(), step.chainJson(), step.counterJson(),
                    step.cardId(), step.stepId()));
        } catch (RestClientException e) {
            log.warn("채점 서버 호출 실패 (stepId={}): {}", step.stepId(), e.toString());
            save(userId, step, req, hash, null, null, null, null, null);
            return new JudgementResponse(null, null, null, Map.of(), null, false, FALLBACK_MESSAGE, null);
        }

        boolean correct = result.score() >= CORRECT_SCORE;
        boolean byClaude = "claude".equals(result.grader());
        Map<String, String> reasons = result.reasons() == null ? Map.of() : result.reasons();
        String feedbackJson = writeFeedback(new StoredFeedback(result.feedback(), reasons));
        save(userId, step, req, hash, correct, result.score(), result.rubric(), byClaude ? "llm" : "rule", feedbackJson);
        // TODO(P17): B의 recordConceptResult(userId, step.conceptIds(), correct) 가 생기면 여기서 부른다
        return new JudgementResponse(result.score(), correct, result.rubric(), reasons,
                byClaude ? "claude" : "rule", false, null, result.feedback());
    }

    private void save(String userId, JudgementStep step, JudgementRequest req, String hash, Boolean correct,
                      Integer score, Rubric rubric, String gradedBy, String feedbackJson) {
        repository.insertAnswer(userId, step.cardId(), step.stepId(), req.choice(), req.answer(), hash,
                correct, score, rubric, gradedBy, feedbackJson);
    }

    /** 피드백이 없으면 null 을 저장한다 (예: 채점 서버가 피드백을 안 주는 옛 버전). */
    String writeFeedback(StoredFeedback stored) {
        if (stored.feedback() == null && stored.reasons().isEmpty()) {
            return null;
        }
        return json.writeValueAsString(stored);
    }

    /** 저장된 JSON 을 읽는다. 비었거나(#56 이전 줄) 깨졌으면 피드백 없음·이유 없음. */
    StoredFeedback readFeedback(String feedbackJson) {
        if (feedbackJson == null || feedbackJson.isBlank()) {
            return new StoredFeedback(null, Map.of());
        }
        try {
            StoredFeedback stored = json.readValue(feedbackJson, StoredFeedback.class);
            Map<String, String> reasons = stored.reasons() == null ? Map.of() : stored.reasons();
            return new StoredFeedback(stored.feedback(), reasons);
        } catch (JacksonException e) {
            log.warn("저장된 피드백 JSON 을 읽지 못했어요: {}", e.getOriginalMessage());
            return new StoredFeedback(null, Map.of());
        }
    }

    OffsetDateTime startOfTodayKst() {
        return OffsetDateTime.now(clock).atZoneSameInstant(KST).toLocalDate().atStartOfDay(KST).toOffsetDateTime();
    }
}
