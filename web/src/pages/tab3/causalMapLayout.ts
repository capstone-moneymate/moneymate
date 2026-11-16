import type { CausalMap, ForceDir, MapNode } from '@/types/causalMap'

/**
 * 인과 지도 배치 (React Flow 에 넘기기 전 단계, 화면과 무관한 순수 함수). 디자인 시안의 가로 나무 모양.
 *   [나의 인과 지도] ─ [테마] ─ 개념(깊이 0) ─ 개념(깊이 1) ─ …
 * - 테마마다 가로 띠 하나. 띠 안에서 개념은 테마 안 연결의 가장 긴 경로(깊이)로 열을 나눠, 원인이 왼쪽·결과가 오른쪽에 온다.
 * - 접힌 테마는 테마 노드만 남고, 그 테마 개념으로 드나드는 연결은 테마 노드로 합친다.
 * - 외부 배치 라이브러리는 쓰지 않는다.
 */

export const ROOT_W = 104
export const ROOT_H = 36
export const THEME_W = 92
export const THEME_H = 32
export const NODE_W = 108
export const NODE_H = 36
const COL_GAP = 32
const ROW_GAP = 10
const BAND_GAP = 24

const THEME_X = ROOT_W + COL_GAP
const CONCEPT_X = THEME_X + THEME_W + COL_GAP
const COL_STEP = NODE_W + COL_GAP

/** 정답률이 이보다 낮으면 "복습 필요" (임시 기준, 팀이 정하면 바꾼다). 한 번도 안 푼 개념은 표시하지 않는다 */
export const REVIEW_BELOW = 0.5
export const needsReview = (n: Pick<MapNode, 'correct' | 'total'>) =>
  n.total > 0 && n.correct / n.total < REVIEW_BELOW

export const ROOT_ID = 'root'
export const themeId = (theme: string) => `theme:${theme}`

/** 접은 뒤 합친 연결은 up·down 이 섞일 수 있다 */
export type LayoutEdgeDir = ForceDir | 'mixed'

interface Box {
  id: string
  x: number
  y: number
}

export type LayoutNode =
  | (Box & { kind: 'root' })
  | (Box & { kind: 'theme'; theme: string; collapsed: boolean; count: number })
  | (Box & { kind: 'concept'; node: MapNode })

export interface CausalLayoutEdge {
  kind: 'causal'
  id: string
  source: string
  target: string
  dir: LayoutEdgeDir
  /** 합쳐진 원래 연결 수 (접지 않은 연결은 1) */
  count: number
}

export type LayoutEdge =
  /** 뿌리→테마, 테마→첫 열 개념. 테마 색 가지 */
  | { kind: 'branch'; id: string; source: string; target: string; theme: string }
  /** 개념 사이 인과 연결 (접히면 테마 노드로 합쳐짐) */
  | CausalLayoutEdge

export interface Layout {
  nodes: LayoutNode[]
  edges: LayoutEdge[]
}

/** 테마 순서는 응답에 처음 나온 순서 */
export const themesOf = (map: CausalMap): string[] => {
  const seen: string[] = []
  for (const n of map.nodes) if (!seen.includes(n.theme)) seen.push(n.theme)
  return seen
}

/** 테마 안 연결만으로 깊이(시작 개념에서 가장 긴 경로)를 매긴다. 순환이 있어도 끝나도록 개념 수만큼만 돈다 */
const depthsOf = (members: MapNode[], map: CausalMap): Map<string, number> => {
  const ids = new Set(members.map((m) => m.id))
  const inner = map.edges.filter((e) => ids.has(e.from) && ids.has(e.to) && e.from !== e.to)
  const depth = new Map(members.map((m) => [m.id, 0]))
  for (let i = 0; i < members.length; i++) {
    let changed = false
    for (const e of inner) {
      const next = depth.get(e.from)! + 1
      if (next > depth.get(e.to)! && next < members.length) {
        depth.set(e.to, next)
        changed = true
      }
    }
    if (!changed) break
  }
  return depth
}

const ROW_H = NODE_H + ROW_GAP

export const buildLayout = (map: CausalMap, collapsed: ReadonlySet<string>): Layout => {
  const nodes: LayoutNode[] = []
  const edges: LayoutEdge[] = []
  /** 개념 id → 화면에 보이는 노드 id (접힌 테마면 테마 노드) */
  const visibleOf = new Map<string, string>()
  let y = 0

  for (const theme of themesOf(map)) {
    const members = map.nodes.filter((n) => n.theme === theme)
    const tid = themeId(theme)
    edges.push({ kind: 'branch', id: `${ROOT_ID}->${tid}`, source: ROOT_ID, target: tid, theme })

    if (collapsed.has(theme)) {
      members.forEach((m) => visibleOf.set(m.id, tid))
      nodes.push({
        kind: 'theme',
        id: tid,
        x: THEME_X,
        y,
        theme,
        collapsed: true,
        count: members.length,
      })
      y += THEME_H + BAND_GAP
      continue
    }

    const depth = depthsOf(members, map)
    const deepest = Math.max(0, ...depth.values())
    const cols: MapNode[][] = []
    for (let d = 0; d <= deepest; d++) cols.push(members.filter((m) => depth.get(m.id) === d))
    const bandH = Math.max(THEME_H, Math.max(...cols.map((c) => c.length)) * ROW_H - ROW_GAP)

    // 열마다 세로 가운데 정렬. 깊이 1 이상은 왼쪽 부모들의 평균 높이 순으로 놓아 선이 덜 꼬이게 한다
    const placedY = new Map<string, number>()
    cols.forEach((col, d) => {
      if (d > 0) {
        const center = (m: MapNode) => {
          const ys = map.edges
            .filter((e) => e.to === m.id && placedY.has(e.from))
            .map((e) => placedY.get(e.from)!)
          return ys.length ? ys.reduce((s, v) => s + v, 0) / ys.length : members.indexOf(m) * ROW_H
        }
        col.sort((a, b) => center(a) - center(b))
      }
      const top = y + (bandH - (col.length * ROW_H - ROW_GAP)) / 2
      col.forEach((m, i) => {
        const ny = top + i * ROW_H
        placedY.set(m.id, ny)
        visibleOf.set(m.id, m.id)
        nodes.push({ kind: 'concept', id: m.id, x: CONCEPT_X + d * COL_STEP, y: ny, node: m })
        if (d === 0) {
          edges.push({ kind: 'branch', id: `${tid}->${m.id}`, source: tid, target: m.id, theme })
        }
      })
    })

    nodes.push({
      kind: 'theme',
      id: tid,
      x: THEME_X,
      y: y + bandH / 2 - THEME_H / 2,
      theme,
      collapsed: false,
      count: members.length,
    })
    y += bandH + BAND_GAP
  }

  const totalH = Math.max(ROOT_H, y - BAND_GAP)
  nodes.unshift({ kind: 'root', id: ROOT_ID, x: 0, y: totalH / 2 - ROOT_H / 2 })

  // 인과 연결을 보이는 노드 기준으로 옮기고, 같은 쌍은 하나로 합친다
  const merged = new Map<string, CausalLayoutEdge>()
  for (const e of map.edges) {
    const source = visibleOf.get(e.from)
    const target = visibleOf.get(e.to)
    if (!source || !target || source === target) continue // 사전에 없는 개념, 접힌 테마 안쪽 연결
    const id = `${source}=>${target}`
    const prev = merged.get(id)
    if (!prev) {
      merged.set(id, { kind: 'causal', id, source, target, dir: e.forceDir, count: 1 })
    } else {
      prev.count += 1
      if (prev.dir !== e.forceDir) prev.dir = 'mixed'
    }
  }
  edges.push(...merged.values())

  return { nodes, edges }
}
