import type { CausalMap, ForceDir, MapEdge, MapNode } from '@/types/causalMap'

/**
 * 인과 지도 배치 (React Flow 에 넘기기 전 단계, 화면과 무관한 순수 함수). 마인드맵 모양.
 *
 *   개념 ─ 개념 ─ [테마] ─┐                 ┌─ [테마] ─ 개념 ─ 개념
 *                        [나의 인과 지도]
 *   개념 ─ [테마] ────────┘                 └─ [테마] ─ 개념
 *
 * - 가운데 뿌리, 테마는 왼쪽·오른쪽으로 나눠 단다 (높이가 비슷해지게 번갈아).
 * - 테마 띠 안에서 개념은 테마 안 연결의 가장 긴 경로(깊이)로 열을 나눠, 원인이 안쪽·결과가 바깥쪽에 온다.
 * - 선이 엉키지 않게 처음에는 "가지 + 같은 테마 안 인과선"만 그린다.
 *   다른 테마로 가는 연결·아직 안 배운 개념과의 연결은 개념 노드에 +N 으로만 표시한다.
 * - 개념을 고르면(focus) 그 개념의 연결을 전부 그린다. 아직 안 배운 개념·접힌 테마의 개념은
 *   고른 개념 옆에 임시 노드(ghost)로 놓는다: 결과 쪽은 바깥, 원인 쪽은 안쪽.
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
const ROW_H = NODE_H + ROW_GAP

const THEME_X = ROOT_W / 2 + COL_GAP
const CONCEPT_X = THEME_X + THEME_W + COL_GAP
const COL_STEP = NODE_W + COL_GAP

export const ROOT_ID = 'root'
export const themeId = (theme: string) => `theme:${theme}`
const ghostId = (conceptId: string) => `ghost:${conceptId}`
/** 임시 이웃을 놓을 빈 열을 찾을 때 몇 열까지 더 나가 볼지 */
const MAX_GHOST_STEPS = 6

/** 노드가 뿌리의 어느 쪽에 있나. 선은 안쪽에서 들어와 바깥쪽으로 나간다 */
export type Side = 'left' | 'right'

interface Box {
  id: string
  x: number
  y: number
}

export type LayoutNode =
  | (Box & { kind: 'root' })
  | (Box & { kind: 'theme'; side: Side; theme: string; collapsed: boolean; count: number })
  /** hidden: 처음 화면에 안 그린 연결 수 (+N 표시) */
  | (Box & { kind: 'concept'; side: Side; node: MapNode; hidden: number })
  /** 고른 개념 옆에 임시로 놓은 이웃 (아직 안 배운 개념, 접힌 테마의 개념) */
  | (Box & { kind: 'ghost'; side: Side; node: MapNode })

export type LayoutEdge =
  /** 뿌리→테마, 테마→첫 열 개념. 테마 색 가지 */
  | { kind: 'branch'; id: string; source: string; target: string; theme: string; side: Side }
  /** 개념 사이 인과 연결. focus: 고른 개념 때문에 새로 그린 선 */
  | { kind: 'causal'; id: string; source: string; target: string; dir: ForceDir; focus: boolean }

export interface Layout {
  nodes: LayoutNode[]
  edges: LayoutEdge[]
}

/** 배운 개념(learned)만. 처음 화면과 홈 요약 카드가 같은 기준을 쓴다 */
export const learnedOf = (map: CausalMap): MapNode[] => map.nodes.filter((n) => n.learned)

/** 테마 순서는 배운 개념이 응답에 처음 나온 순서 */
export const themesOf = (map: CausalMap): string[] => {
  const seen: string[] = []
  for (const n of learnedOf(map)) if (!seen.includes(n.theme)) seen.push(n.theme)
  return seen
}

/** 처음 화면에 그리는 인과선: 양 끝이 모두 배운 개념이고 같은 테마 */
export const isBaseEdge = (e: MapEdge, byId: ReadonlyMap<string, MapNode>) => {
  const a = byId.get(e.from)
  const b = byId.get(e.to)
  return !!a && !!b && a.learned && b.learned && a.theme === b.theme && e.from !== e.to
}

/** 테마 안 연결만으로 깊이(시작 개념에서 가장 긴 경로)를 매긴다. 순환이 있어도 끝나도록 개념 수만큼만 돈다 */
const depthsOf = (members: MapNode[], edges: MapEdge[]): Map<string, number> => {
  const ids = new Set(members.map((m) => m.id))
  const inner = edges.filter((e) => ids.has(e.from) && ids.has(e.to) && e.from !== e.to)
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

interface Band {
  theme: string
  members: MapNode[]
  collapsed: boolean
  cols: MapNode[][]
  height: number
}

const bandOf = (theme: string, members: MapNode[], edges: MapEdge[], collapsed: boolean): Band => {
  if (collapsed) return { theme, members, collapsed, cols: [], height: THEME_H }
  const depth = depthsOf(members, edges)
  const deepest = Math.max(0, ...depth.values())
  const cols: MapNode[][] = []
  for (let d = 0; d <= deepest; d++) cols.push(members.filter((m) => depth.get(m.id) === d))
  const height = Math.max(THEME_H, Math.max(...cols.map((c) => c.length)) * ROW_H - ROW_GAP)
  return { theme, members, collapsed, cols, height }
}

/** 개념 열 d 의 왼쪽 x. 왼쪽 가지는 거울처럼 뒤집는다 */
const conceptX = (side: Side, d: number) =>
  side === 'right' ? CONCEPT_X + d * COL_STEP : -(CONCEPT_X + d * COL_STEP) - NODE_W
const themeX = (side: Side) => (side === 'right' ? THEME_X : -THEME_X - THEME_W)

export const buildLayout = (
  map: CausalMap,
  collapsed: ReadonlySet<string>,
  focusId: string | null = null,
): Layout => {
  const byId = new Map(map.nodes.map((n) => [n.id, n]))
  const learned = learnedOf(map)
  const baseEdges = map.edges.filter((e) => isBaseEdge(e, byId))

  // 1. 테마 띠를 만들고 왼쪽·오른쪽 중 지금 더 낮은 쪽에 단다 (오른쪽부터)
  const sides: Record<Side, Band[]> = { left: [], right: [] }
  const used: Record<Side, number> = { left: 0, right: 0 }
  for (const theme of themesOf(map)) {
    const band = bandOf(
      theme,
      learned.filter((n) => n.theme === theme),
      baseEdges,
      collapsed.has(theme),
    )
    const side: Side = used.right <= used.left ? 'right' : 'left'
    sides[side].push(band)
    used[side] += band.height + BAND_GAP
  }

  const nodes: LayoutNode[] = [{ kind: 'root', id: ROOT_ID, x: -ROOT_W / 2, y: -ROOT_H / 2 }]
  const edges: LayoutEdge[] = []
  /** 화면에 놓인 개념 → 위치·쪽 (focus 이웃을 놓을 때 쓴다) */
  const placed = new Map<string, { x: number; y: number; side: Side }>()

  // 2. 쪽마다 띠를 위에서 아래로 쌓고, 전체를 뿌리 높이(0) 가운데로 맞춘다
  for (const side of ['right', 'left'] as const) {
    const bands = sides[side]
    const total = bands.reduce((s, b) => s + b.height, 0) + BAND_GAP * Math.max(0, bands.length - 1)
    let y = -total / 2
    for (const band of bands) {
      const tid = themeId(band.theme)
      edges.push({
        kind: 'branch',
        id: `${ROOT_ID}->${tid}`,
        source: ROOT_ID,
        target: tid,
        theme: band.theme,
        side,
      })
      nodes.push({
        kind: 'theme',
        id: tid,
        side,
        x: themeX(side),
        y: y + band.height / 2 - THEME_H / 2,
        theme: band.theme,
        collapsed: band.collapsed,
        count: band.members.length,
      })

      // 열마다 세로 가운데 정렬. 깊이 1 이상은 안쪽 부모들의 평균 높이 순으로 놓아 선이 덜 꼬이게 한다
      band.cols.forEach((col, d) => {
        if (d > 0) {
          const center = (m: MapNode) => {
            const ys = baseEdges
              .filter((e) => e.to === m.id && placed.has(e.from))
              .map((e) => placed.get(e.from)!.y)
            return ys.length
              ? ys.reduce((s, v) => s + v, 0) / ys.length
              : band.members.indexOf(m) * ROW_H
          }
          col.sort((a, b) => center(a) - center(b))
        }
        const top = y + (band.height - (col.length * ROW_H - ROW_GAP)) / 2
        col.forEach((m, i) => {
          const ny = top + i * ROW_H
          const nx = conceptX(side, d)
          placed.set(m.id, { x: nx, y: ny, side })
          const hidden = map.edges.filter(
            (e) => (e.from === m.id || e.to === m.id) && !isBaseEdge(e, byId),
          ).length
          nodes.push({ kind: 'concept', id: m.id, side, x: nx, y: ny, node: m, hidden })
          if (d === 0) {
            edges.push({
              kind: 'branch',
              id: `${tid}->${m.id}`,
              source: tid,
              target: m.id,
              theme: band.theme,
              side,
            })
          }
        })
      })
      y += band.height + BAND_GAP
    }
  }

  // 3. 처음 화면의 인과선 (같은 테마 안, 접힌 테마는 빼고)
  for (const e of baseEdges) {
    if (!placed.has(e.from) || !placed.has(e.to)) continue
    edges.push({
      kind: 'causal',
      id: `${e.from}=>${e.to}`,
      source: e.from,
      target: e.to,
      dir: e.forceDir,
      focus: false,
    })
  }

  // 4. 고른 개념의 나머지 연결. 화면에 없는 이웃은 고른 개념 옆에 임시 노드로 놓는다
  const anchor = focusId ? placed.get(focusId) : undefined
  if (focusId && anchor) {
    const outward = anchor.side === 'right' ? 1 : -1
    const ghosts: { out: MapNode[]; in: MapNode[] } = { out: [], in: [] }
    const ghostIds = new Set<string>()
    const extra = map.edges.filter(
      (e) => (e.from === focusId || e.to === focusId) && !isBaseEdge(e, byId) && e.from !== e.to,
    )
    for (const e of extra) {
      const otherId = e.from === focusId ? e.to : e.from
      const other = byId.get(otherId)
      if (!other) continue // 사전에 없는 개념
      if (!placed.has(otherId) && !ghostIds.has(otherId)) {
        ghostIds.add(otherId)
        ;(e.from === focusId ? ghosts.out : ghosts.in).push(other)
      }
    }
    // 결과 쪽 이웃은 바깥, 원인 쪽 이웃은 안쪽에 고른 개념 높이 가운데로 쌓는다.
    // 바로 옆 열이 이미 차 있으면 한 열씩 더 나가서 빈 자리를 찾는다 (다른 노드를 가리지 않게)
    const boxes = nodes.map((n) => {
      const [w, h] =
        n.kind === 'root'
          ? [ROOT_W, ROOT_H]
          : n.kind === 'theme'
            ? [THEME_W, THEME_H]
            : [NODE_W, NODE_H]
      return { x: n.x, y: n.y, w, h }
    })
    const free = (x: number, top: number, bottom: number) =>
      !boxes.some((b) => b.x < x + NODE_W && x < b.x + b.w && b.y < bottom && top < b.y + b.h)
    for (const [list, step] of [
      [ghosts.out, outward],
      [ghosts.in, -outward],
    ] as const) {
      if (list.length === 0) continue
      const top = anchor.y - ((list.length - 1) * ROW_H) / 2
      const bottom = top + list.length * ROW_H - ROW_GAP
      let x = anchor.x + step * COL_STEP
      for (let k = 1; k <= MAX_GHOST_STEPS && !free(x, top, bottom); k++) {
        x = anchor.x + step * (k + 1) * COL_STEP
      }
      list.forEach((n, i) => {
        const g = { x, y: top + i * ROW_H }
        boxes.push({ ...g, w: NODE_W, h: NODE_H })
        nodes.push({ kind: 'ghost', id: ghostId(n.id), side: anchor.side, ...g, node: n })
      })
    }
    const visibleId = (id: string) => (placed.has(id) ? id : ghostId(id))
    for (const e of extra) {
      if (!byId.has(e.from) || !byId.has(e.to)) continue
      edges.push({
        kind: 'causal',
        id: `focus:${e.from}=>${e.to}`,
        source: visibleId(e.from),
        target: visibleId(e.to),
        dir: e.forceDir,
        focus: true,
      })
    }
  }

  return { nodes, edges }
}
