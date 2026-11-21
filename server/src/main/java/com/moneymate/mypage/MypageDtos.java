package com.moneymate.mypage;

import java.util.List;

/** 탭3 마이페이지 API 응답. 필드 이름은 camelCase, 개념 id 는 concepts.id 문자열 그대로. */
public final class MypageDtos {

    private MypageDtos() {
    }

    /**
     * 지도의 점 하나.
     *
     * @param learned true = 내가 배운 개념(total > 0), false = 배운 개념과 연결된 아직 안 배운 개념(correct·total 0)
     */
    public record MapNode(String id, String name, String theme, int correct, int total, boolean learned) {
    }

    /** 지도의 화살표 하나. "from 이 커지면 to 를 올린다(up) / 누른다(down)". */
    public record MapEdge(String from, String to, String forceDir) {
    }

    /** GET /api/mypage/map */
    public record CausalMap(List<MapNode> nodes, List<MapEdge> edges) {
    }

    /** 다시 보는 개념 하나. accuracy 는 소수(0.5 = 50%). */
    public record ReviewConcept(String id, String name, String theme, int correct, int total, double accuracy) {
    }

    /** GET /api/mypage/review */
    public record Review(List<ReviewConcept> concepts) {
    }

    /**
     * GET /api/mypage/summary. 마이페이지 홈 위쪽 숫자.
     *
     * @param streakDays     연속 학습 일수 (KST). 오늘 아직 안 풀었으면 어제까지 이어진 날수, 어제도 안 풀었으면 0
     * @param studiedToday   오늘(KST) 답안을 냈는가
     * @param conceptCount   배운 개념 수 (user_concepts.total > 0)
     * @param accuracy       종합 정답률 소수 (객관식 정답 + 판단 60점 이상) / 채점된 답안. 채점된 답안이 없으면 null
     * @param gradedCount    채점된 답안 수 (accuracy 의 분모)
     * @param judgementCount 판단해보기 제출 수
     */
    public record Summary(int streakDays, boolean studiedToday, int conceptCount, Double accuracy,
                          int gradedCount, int judgementCount) {
    }

    /**
     * 학습 달력의 카드 하나. 그날 마지막으로 낸 답안 기준.
     *
     * @param cardDate  카드가 노출된 날 (yyyy-MM-dd)
     * @param stepCount 문제 수 (concept 단계 제외)
     * @param answered  그날 답한 문제 수
     * @param graded    채점된 문제 수
     * @param correct   맞은 문제 수
     */
    public record CalendarCard(String cardId, String title, String cardDate, int stepCount,
                               int answered, int graded, int correct) {
    }

    /** 문제를 푼 하루 (KST, yyyy-MM-dd). 카드는 그날 처음 푼 순서 */
    public record CalendarDay(String date, List<CalendarCard> cards) {
    }

    /** GET /api/mypage/calendar. 최근 400일, 최근 날짜 먼저. 기록이 없으면 빈 배열 */
    public record Calendar(List<CalendarDay> days) {
    }
}
