package com.moneymate.answer;

import com.moneymate.answer.GhostDtos.Attempt;
import com.moneymate.answer.GhostDtos.AttemptInfo;
import com.moneymate.answer.GhostDtos.Cell;
import com.moneymate.answer.GhostDtos.Comparison;
import com.moneymate.answer.GhostDtos.Report;
import com.moneymate.answer.GhostDtos.Row;
import com.moneymate.answer.GhostDtos.StepRecord;
import com.moneymate.answer.GhostRepository.GhostStep;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/**
 * 고스트 비교 계산 (계획 2-6). 같은 카드를 다시 풀었을 때 "지난번의 나"와 "이번의 나"를 단계별로 나란히 놓는다.
 * DB 를 모르는 순수 계산이라 손계산 예시로 테스트한다 (GhostTest).
 *
 * <ul>
 *   <li>시도 = user_answers.attempt_no (#215). 끝까지 푼 시도 = 카드의 답 단계(개념 단계 제외)를 모두 낸 시도</li>
 *   <li>이번 = 가장 최근 시도, 지난번 = 그 앞의 끝까지 푼 시도 중 가장 최근</li>
 *   <li>좋아졌다: ① 틀림 → 맞힘 ② 둘 다 맞혔으면 초가 줄었을 때. 판단해보기는 시간 대신 점수가 올랐을 때</li>
 *   <li>최고 기록: 이번보다 앞선 기록이 {@link #MIN_EARLIER}번 이상 있을 때만. 1번뿐이면 "지난번보다"와 같은 말이다</li>
 * </ul>
 * 시간은 화면에 보이는 초 단위(반올림)로 비교한다. 한 번씩 잰 값이라 우연과 구분하는 검정은 할 수 없어서,
 * 보이는 숫자가 줄었을 때만 줄었다고 한다. 정답이 시간보다 먼저다.
 */
public final class Ghost {

    /** 최고 기록을 따지려면 필요한 이전 기록 수 (저희가 정한 값) */
    static final int MIN_EARLIER = 2;

    static final int SURE = 2;

    private Ghost() {
    }

    public static Report report(List<GhostStep> steps, List<GhostRow> rows) {
        if (steps.isEmpty() || rows.isEmpty()) {
            return new Report(null, null);
        }
        // 시도 번호 → (단계 → 그 시도의 마지막 답안)
        TreeMap<Integer, Map<Long, GhostRow>> attempts = new TreeMap<>();
        for (GhostRow r : rows) {
            attempts.computeIfAbsent(r.attemptNo(), k -> new TreeMap<>()).put(r.stepId(), r);
        }
        int currentNo = attempts.lastKey();
        Integer lastCompleteNo = null;
        Integer previousNo = null;
        for (Map.Entry<Integer, Map<Long, GhostRow>> e : attempts.entrySet()) {
            if (!complete(steps, e.getValue())) {
                continue;
            }
            lastCompleteNo = e.getKey();
            if (e.getKey() < currentNo) {
                previousNo = e.getKey();
            }
        }
        Attempt lastComplete = lastCompleteNo == null ? null
                : attempt(lastCompleteNo, steps, attempts.get(lastCompleteNo));
        Comparison comparison = previousNo == null ? null : compare(steps, attempts, previousNo, currentNo);
        return new Report(lastComplete, comparison);
    }

    static boolean complete(List<GhostStep> steps, Map<Long, GhostRow> answers) {
        return steps.stream().allMatch(s -> answers.containsKey(s.stepId()));
    }

    private static Comparison compare(List<GhostStep> steps, TreeMap<Integer, Map<Long, GhostRow>> attempts,
                                      int previousNo, int currentNo) {
        Map<Long, GhostRow> prev = attempts.get(previousNo);
        Map<Long, GhostRow> cur = attempts.get(currentNo);
        List<Row> out = new ArrayList<>();
        for (GhostStep s : steps) {
            boolean judged = "judgement".equals(s.kind());
            Cell p = cell(prev.get(s.stepId()), judged);
            Cell c = cell(cur.get(s.stepId()), judged);
            List<Cell> earlier = attempts.headMap(currentNo).values().stream()
                    .map(a -> cell(a.get(s.stepId()), judged)).filter(Objects::nonNull).toList();
            out.add(new Row(String.valueOf(s.stepId()), s.kind(), p, c,
                    improved(p, c, judged), best(earlier, c, judged)));
        }
        int improvedSteps = (int) out.stream().filter(Row::improved).count();
        return new Comparison(info(previousNo, prev), info(currentNo, cur), out, improvedSteps);
    }

    /** 지난번보다 좋아졌는가. 정답이 먼저, 둘 다 맞혔을 때만 시간을 본다 */
    static boolean improved(Cell p, Cell c, boolean judged) {
        if (p == null || c == null) {
            return false;
        }
        if (judged) {
            return p.score() != null && c.score() != null && c.score() > p.score();
        }
        if (Boolean.FALSE.equals(p.isCorrect()) && Boolean.TRUE.equals(c.isCorrect())) {
            return true;
        }
        return Boolean.TRUE.equals(p.isCorrect()) && Boolean.TRUE.equals(c.isCorrect())
                && p.seconds() != null && c.seconds() != null && c.seconds() < p.seconds();
    }

    /** 이번 기록이 그 앞의 모든 기록을 넘었는가. earlier 는 이번보다 앞선 시도들의 이 단계 기록 */
    static boolean best(List<Cell> earlier, Cell c, boolean judged) {
        if (c == null || earlier.size() < MIN_EARLIER) {
            return false;
        }
        if (judged) {
            List<Integer> scores = earlier.stream().map(Cell::score).filter(Objects::nonNull).toList();
            return c.score() != null && !scores.isEmpty() && c.score() > scores.stream().mapToInt(i -> i).max().getAsInt();
        }
        if (!Boolean.TRUE.equals(c.isCorrect())) {
            return false;
        }
        List<Cell> right = earlier.stream().filter(e -> Boolean.TRUE.equals(e.isCorrect())).toList();
        if (right.isEmpty()) {
            return true;    // 처음 맞혔다
        }
        List<Integer> times = right.stream().map(Cell::seconds).filter(Objects::nonNull).toList();
        return c.seconds() != null && !times.isEmpty() && c.seconds() < times.stream().mapToInt(i -> i).min().getAsInt();
    }

    private static Attempt attempt(int no, List<GhostStep> steps, Map<Long, GhostRow> answers) {
        List<StepRecord> records = steps.stream().map(s -> new StepRecord(String.valueOf(s.stepId()), s.kind(),
                cell(answers.get(s.stepId()), "judgement".equals(s.kind())))).toList();
        AttemptInfo i = info(no, answers);
        return new Attempt(no, i.date(), i.sureWrong(), records);
    }

    private static AttemptInfo info(int no, Map<Long, GhostRow> answers) {
        GhostRow any = answers.values().iterator().next();
        return new AttemptInfo(no, any.day() == null ? null : any.day().toString(), sureWrong(answers));
    }

    /** "확실해요"라고 하고 틀린 답 수. 그 시도에 확신 기록이 하나도 없으면(확신 버튼 이전 답안) null */
    static Integer sureWrong(Map<Long, GhostRow> answers) {
        if (answers.values().stream().allMatch(r -> r.confidence() == null)) {
            return null;
        }
        return (int) answers.values().stream()
                .filter(r -> Integer.valueOf(SURE).equals(r.confidence()) && Boolean.FALSE.equals(r.isCorrect()))
                .count();
    }

    private static Cell cell(GhostRow r, boolean judged) {
        if (r == null) {
            return null;
        }
        return judged ? new Cell(r.isCorrect(), null, r.score())
                : new Cell(r.isCorrect(), seconds(r.responseMs()), null);
    }

    /** ms → 화면에 보이는 초 (반올림). 1초 미만은 1 */
    static Integer seconds(Integer ms) {
        return ms == null ? null : (int) Math.max(1, Math.round(ms / 1000.0));
    }
}
