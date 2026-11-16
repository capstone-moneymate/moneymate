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
}
