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

/**
 * 판단해보기 근거 채점 (A, #55).
 *
 * 순서: 단계 확인 → 하루 호출 제한 → 같은 답안 해시 재사용 → FastAPI 채점 → user_answers 저장.
 * 채점 자체(루브릭·Claude·규칙 채점 전환)는 Python(worker/generate/judge.py)이 하고, 여기서는 점수를 다시 계산하지 않는다.
 * FastAPI 호출이 실패하면 점수 없이 고정 문구를 돌려주고 답안은 저장한다.
 */
@Service
public class JudgementService {

    private static final Logger log = LoggerFactory.getLogger(JudgementService.class);
    static final ZoneId KST = ZoneId.of("Asia/Seoul");
    /** conventions P17: 60점 이상이면 맞음 */
    static final int CORRECT_SCORE = 60;
    /** 채점 서버 실패 시 문구 (기술확정안 "루브릭"의 고정 문구) */
    static final String FALLBACK_MESSAGE = "근거 있는 선택이었어요. 이런 경우도 생길 수 있어요.";

    private final JudgementRepository repository;
    private final JudgeClient judgeClient;
    private final JudgeProperties props;
    private final Clock clock;

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
            save(userId, step, req, hash, correct, g.score(), rubric, g.gradedBy());
            return new JudgementResponse(g.score(), correct, rubric, Map.of(), "claude", true, null);
        }

        JudgeApiResponse result;
        try {
            result = judgeClient.judge(new JudgeApiRequest(
                    req.answer(), step.keyFactsJson(), step.chainJson(), step.counterJson(),
                    step.cardId(), step.stepId()));
        } catch (RestClientException e) {
            log.warn("채점 서버 호출 실패 (stepId={}): {}", step.stepId(), e.toString());
            save(userId, step, req, hash, null, null, null, null);
            return new JudgementResponse(null, null, null, Map.of(), null, false, FALLBACK_MESSAGE);
        }

        boolean correct = result.score() >= CORRECT_SCORE;
        String gradedBy = "claude".equals(result.grader()) ? "llm" : "rule";
        save(userId, step, req, hash, correct, result.score(), result.rubric(), gradedBy);
        // TODO(P17): B의 recordConceptResult(userId, step.conceptIds(), correct) 가 생기면 여기서 부른다
        Map<String, String> reasons = result.reasons() == null ? Map.of() : result.reasons();
        return new JudgementResponse(result.score(), correct, result.rubric(), reasons,
                "claude".equals(result.grader()) ? "claude" : "rule", false, null);
    }

    private void save(String userId, JudgementStep step, JudgementRequest req, String hash,
                      Boolean correct, Integer score, Rubric rubric, String gradedBy) {
        repository.insertAnswer(userId, step.cardId(), step.stepId(), req.choice(), req.answer(), hash,
                correct, score, rubric, gradedBy);
    }

    OffsetDateTime startOfTodayKst() {
        return OffsetDateTime.now(clock).atZoneSameInstant(KST).toLocalDate().atStartOfDay(KST).toOffsetDateTime();
    }
}
