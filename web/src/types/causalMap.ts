/**
 * 탭3 인과 지도 타입 (잠정). 마이페이지 API GET /api/mypage/map?userId=... 응답 모양.
 * 마이페이지 API(B, Spring Boot)를 만드는 작업과 맞춘 것이고, API가 확정되면 이 파일을 함께 고친다.
 * 인과 지도 = 이 사용자가 학습한 개념·연결의 합집합 (기술확정안 "학습 기록").
 */

/** 연결의 힘 방향 ← causal_edges.force_dir. up: 올리는 힘, down: 누르는 힘 */
export type ForceDir = 'up' | 'down'

/** 지도에 놓이는 개념 하나 */
export interface MapNode {
  /** ← concepts.id */
  id: string
  /** ← concepts.name */
  name: string
  /** 테마(금리, AI·반도체, 차트 읽기 …) ← concepts.theme. 접기 단위 */
  theme: string
  /** 맞힌 횟수 ← user_concepts.correct */
  correct: number
  /** 푼 횟수 ← user_concepts.total */
  total: number
}

/** 개념 사이 연결 하나 (from 이 to 를 올리거나 누른다) */
export interface MapEdge {
  /** ← causal_edges.from_concept */
  from: string
  /** ← causal_edges.to_concept */
  to: string
  forceDir: ForceDir
}

export interface CausalMap {
  nodes: MapNode[]
  edges: MapEdge[]
}
