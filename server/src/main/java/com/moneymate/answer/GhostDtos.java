package com.moneymate.answer;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/** GET /api/answers/ghost 응답 모양 (고스트 비교, 계획 2-6). 숫자와 "좋아졌다" 판단은 모두 서버가 정한다. */
public final class GhostDtos {

    private GhostDtos() {
    }

    /**
     * @param lastComplete 끝까지 푼 시도 중 가장 최근. 다시 푸는 도중 "지난번엔 맞혔어요"에 쓴다. 없으면 null
     * @param comparison   가장 최근 시도와 그 앞의 끝까지 푼 시도 비교. 앞 시도가 없으면 null
     */
    public record Report(Attempt lastComplete, Comparison comparison) {
    }

    /** 한 번의 시도. sureWrong 은 "확실해요"라고 하고 틀린 답 수 (그 시도에 확신 기록이 없으면 null) */
    public record Attempt(int attemptNo, String date, Integer sureWrong, List<StepRecord> steps) {
    }

    public record StepRecord(String stepId, String kind, Cell record) {
    }

    /**
     * 한 단계의 기록.
     *
     * @param isCorrect 맞았는가 (판단은 60점 이상, 채점 못 했으면 null)
     * @param seconds   푸는 데 걸린 초 (반올림, 1초 미만은 1). 판단해보기와 시간 기록이 없는 답안은 null
     * @param score     판단 100점 환산 (판단해보기만)
     */
    public record Cell(@JsonProperty("isCorrect") Boolean isCorrect, Integer seconds, Integer score) {
    }

    /**
     * @param previous      지난번 (끝까지 푼 시도)
     * @param current       이번 (가장 최근 시도)
     * @param rows          답 단계마다 한 줄, 단계 번호 순
     * @param improvedSteps 좋아진 단계 수
     */
    public record Comparison(AttemptInfo previous, AttemptInfo current, List<Row> rows, int improvedSteps) {
    }

    public record AttemptInfo(int attemptNo, String date, Integer sureWrong) {
    }

    /**
     * @param previous 지난번 기록
     * @param current  이번 기록 (이번에 안 낸 단계는 null)
     * @param improved 지난번보다 좋아졌는가 (틀림 → 맞힘, 둘 다 맞혔으면 초가 줄었을 때, 판단은 점수가 올랐을 때)
     * @param best     최고 기록 경신 (이전 기록이 2번 이상 있을 때만 따진다)
     */
    public record Row(String stepId, String kind, Cell previous, Cell current, boolean improved, boolean best) {
    }
}
