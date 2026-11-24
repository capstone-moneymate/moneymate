package com.moneymate.learning;

import com.fasterxml.jackson.annotation.JsonAlias;
import java.util.List;
import java.util.Map;

/**
 * 학습자 상태 조회 응답 (사람2, docs/추가구현_계획.md 2-7). 채점 서버(worker/learner/api.py)가 준 값을 그대로 화면에 넘긴다.
 * 채점 서버는 snake_case(due_total)로 주고 화면에는 camelCase(dueTotal)로 나간다 (@JsonAlias 로 읽기만 맞춘다).
 * 숫자는 모두 채점 서버가 계산했다. 여기서는 계산하지 않는다.
 */
public final class LearnerDtos {

    private LearnerDtos() {
    }

    /**
     * 오늘 복습할 개념 (GET /learner/reviews).
     *
     * @param limit     하루 복습 개념 수 상한
     * @param doneToday 오늘 이미 복습한 개념 수
     * @param dueTotal  복습일이 된 개념 전체 수 (상한에 잘리기 전)
     * @param items     오늘 복습할 개념. 앞에서부터 푼다
     */
    public record ReviewQueue(
            int limit,
            @JsonAlias("done_today") int doneToday,
            @JsonAlias("due_total") int dueTotal,
            List<ReviewItem> items) {
    }

    /**
     * @param concept        개념 이름
     * @param pKnow          알 확률 (BKT)
     * @param retrievability 지금 기억하고 있을 확률 (FSRS)
     * @param reason         sure_wrong = 확실해요라고 했는데 틀렸던 개념, due = 복습일이 됨
     * @param dueAt          복습일 (ISO 시각)
     */
    public record ReviewItem(
            @JsonAlias("node_id") long nodeId,
            String concept,
            @JsonAlias("p_know") double pKnow,
            double retrievability,
            String reason,
            @JsonAlias("due_at") String dueAt) {
    }

    /**
     * 복습 문제 하나 (POST /learner/review/quiz). 정답과 해설은 들어 있지 않다 (채점 서버가 보관).
     *
     * @param kind    용어 뜻 / 헷갈리는 쌍 / 틀린 설명 / O/X (헷갈리는 쌍의 보기는 두 개념 이름)
     * @param content 화면용. 보기 고르기는 {question, options}, O/X 는 {statement, options}
     * @param guessP  찍어서 맞힐 확률 (채점 서버가 계산)
     */
    public record ReviewQuiz(
            @JsonAlias("quiz_id") long quizId,
            @JsonAlias("node_id") long nodeId,
            String concept,
            String kind,
            Map<String, Object> content,
            @JsonAlias("guess_p") double guessP) {
    }

    /**
     * 복습 문제 채점 결과 (POST /learner/review/answer).
     *
     * @param key   정답 보기 번호
     * @param pKnow 반영한 뒤의 알 확률 (BKT)
     * @param dueAt 다음 복습일 (ISO 시각)
     */
    public record ReviewResult(
            boolean correct,
            Object key,
            String explanation,
            String concept,
            @JsonAlias("p_know") double pKnow,
            @JsonAlias("due_at") String dueAt) {
    }

    /**
     * 확신 보정 (GET /learner/calibration).
     *
     * @param all               전체
     * @param recent            최근 recentDays 일
     * @param earlier           그 전
     * @param sureWrongConcepts 확실해요라고 했는데 틀렸고 아직 다시 맞히지 못한 개념 이름
     */
    public record Calibration(
            CalibrationSummary all,
            CalibrationSummary recent,
            CalibrationSummary earlier,
            @JsonAlias("recent_days") int recentDays,
            @JsonAlias("sure_wrong_concepts") List<String> sureWrongConcepts) {
    }

    /**
     * 정답/오답 × 확실/헷갈려요 2 × 2 표 하나의 개수와 지표. 분모가 0 인 지표는 null.
     *
     * @param enough         답이 충분한가 (20개 이상). 아니면 화면은 비율을 보여 주지 않는다
     * @param sureWrong      확실해요인데 틀림
     * @param sensitivity    맞힌 답 중 확실해요 비율
     * @param specificity    틀린 답 중 헷갈려요 비율
     * @param illusion       틀린 답 중 확실해요 비율
     * @param sureAccuracy   확실해요 답의 정답률
     * @param unsureAccuracy 헷갈려요 답의 정답률
     * @param bias           확실해요 비율 - 정답률. 양수면 과신
     */
    public record CalibrationSummary(
            int total,
            boolean enough,
            @JsonAlias("sure_right") int sureRight,
            @JsonAlias("sure_wrong") int sureWrong,
            @JsonAlias("unsure_right") int unsureRight,
            @JsonAlias("unsure_wrong") int unsureWrong,
            Double sensitivity,
            Double specificity,
            Double illusion,
            @JsonAlias("sure_accuracy") Double sureAccuracy,
            @JsonAlias("unsure_accuracy") Double unsureAccuracy,
            Double gap,
            Double gamma,
            Double bias) {
    }
}
