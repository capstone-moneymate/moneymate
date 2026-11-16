import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  Background,
  BackgroundVariant,
  MarkerType,
  ReactFlow,
  useReactFlow,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  buildLayout,
  NODE_H,
  NODE_W,
  ROOT_H,
  ROOT_W,
  THEME_H,
  THEME_W,
  themeId,
  themesOf,
} from '@/pages/tab3/causalMapLayout'
import { EDGE_COLORS, themeColorMap } from '@/pages/tab3/mapColors'
import { ConceptNode, GhostNode, RootNode, ThemeNode } from '@/pages/tab3/MapNodes'
import type { CausalMap, MapNode } from '@/types/causalMap'

const nodeTypes = { root: RootNode, theme: ThemeNode, concept: ConceptNode, ghost: GhostNode }

/**
 * 화면을 어디에 맞출지. n 은 같은 대상을 다시 눌러도 effect 가 다시 돌게 하는 번호다.
 * - all: 전체
 * - theme: 편 테마(그 테마로 맞춤) / 접은 테마(그 노드를 가운데로)
 * - concept: 고른 개념과 이웃
 */
type FitRequest =
  | { kind: 'all' }
  /** 첫 화면: 뿌리와 테마 노드만 읽히는 크기로 맞춘다 (개념은 손가락으로 축소해서 본다) */
  | { kind: 'themes' }
  | { kind: 'theme'; theme: string; expanded: boolean }
  | { kind: 'concept'; id: string }
type FitTarget = FitRequest & { n: number }

interface CausalMapViewProps {
  map: CausalMap
  /** 처음부터 고를 개념 id (홈의 다시 보는 개념에서 눌러 들어올 때) */
  focusId?: string | null
}

/**
 * 인과 지도 (React Flow, 마인드맵 모양). 배운 개념만 그린다.
 * 처음에는 가지와 같은 테마 안 인과선만 보이고, 개념을 누르면 그 개념의 연결이 전부(다른 테마·아직 안 배운 개념) 보인다.
 * 테마 노드를 누르면 접고 편다.
 */
export const CausalMapView = ({ map, focusId = null }: CausalMapViewProps) => {
  const themes = useMemo(() => themesOf(map), [map])
  const colors = useMemo(() => themeColorMap(themes), [themes])
  const byId = useMemo(() => new Map(map.nodes.map((n) => [n.id, n])), [map])
  const focus = focusId && byId.get(focusId)?.learned ? focusId : null

  const [collapsed, setCollapsed] = useState<ReadonlySet<string>>(() => new Set())
  const [selectedId, setSelectedId] = useState<string | null>(focus)
  const [fitTarget, setFitTarget] = useState<FitTarget>(
    focus ? { kind: 'concept', id: focus, n: 0 } : { kind: 'themes', n: 0 },
  )
  const { fitView, setCenter, getZoom, getNode, zoomIn, zoomOut } = useReactFlow()

  // 고른 개념이 접혀 사라지면 선택을 지운다 (렌더 중 판정, effect 불필요)
  const selected =
    selectedId && byId.get(selectedId)?.learned && !collapsed.has(byId.get(selectedId)!.theme)
      ? byId.get(selectedId)!
      : null

  const layout = useMemo(
    () => buildLayout(map, collapsed, selected?.id ?? null),
    [map, collapsed, selected],
  )

  /** 고른 개념과 바로 이어진 노드 (나머지는 흐리게) */
  const neighbors = useMemo(() => {
    if (!selected) return null
    const ids = new Set([selected.id])
    for (const e of layout.edges) {
      if (e.kind === 'branch') continue
      if (e.source === selected.id) ids.add(e.target)
      if (e.target === selected.id) ids.add(e.source)
    }
    return ids
  }, [selected, layout])

  const nextFit = (t: FitRequest) => setFitTarget((prev) => ({ ...t, n: prev.n + 1 }))

  const toggleTheme = (theme: string) => {
    const expanding = collapsed.has(theme)
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (expanding) next.delete(theme)
      else next.add(theme)
      return next
    })
    nextFit({ kind: 'theme', theme, expanded: expanding })
  }

  const nodes: Node[] = useMemo(
    () =>
      layout.nodes.map((n): Node => {
        const dim = neighbors !== null && !neighbors.has(n.id)
        const position = { x: n.x, y: n.y }
        switch (n.kind) {
          case 'root':
            return { id: n.id, type: 'root', position, width: ROOT_W, height: ROOT_H, data: {} }
          case 'theme':
            return {
              id: n.id,
              type: 'theme',
              position,
              width: THEME_W,
              height: THEME_H,
              style: { opacity: selected ? 0.35 : 1 },
              data: {
                side: n.side,
                theme: n.theme,
                color: colors.get(n.theme)!,
                collapsed: n.collapsed,
                count: n.count,
              },
            }
          case 'concept':
            return {
              id: n.id,
              type: 'concept',
              position,
              width: NODE_W,
              height: NODE_H,
              data: {
                side: n.side,
                node: n.node,
                hidden: n.hidden,
                dim,
                selected: n.id === selectedId,
              },
            }
          case 'ghost':
            return {
              id: n.id,
              type: 'ghost',
              position,
              width: NODE_W,
              height: NODE_H,
              zIndex: 10,
              data: { side: n.side, node: n.node },
            }
        }
      }),
    [layout, neighbors, selectedId, selected, colors],
  )

  const edges: Edge[] = useMemo(
    () =>
      layout.edges.map((e): Edge => {
        const base = { id: e.id, source: e.source, target: e.target }
        if (e.kind === 'branch') {
          return {
            ...base,
            sourceHandle: e.source === 'root' ? e.side : undefined,
            style: {
              stroke: colors.get(e.theme),
              strokeWidth: 2,
              opacity: selected ? 0.12 : 0.55,
            },
          }
        }
        const touches = selected !== null && (e.source === selected.id || e.target === selected.id)
        const color = EDGE_COLORS[e.dir]
        return {
          ...base,
          zIndex: e.focus ? 5 : 0,
          style: {
            stroke: color,
            strokeWidth: touches ? 2 : 1.5,
            opacity: selected && !touches ? 0.1 : 1,
          },
          markerEnd: { type: MarkerType.ArrowClosed, color, width: 12, height: 12 },
        }
      }),
    [layout, selected, colors],
  )

  // 화면 맞춤은 새 요청(fitTarget.n)이 있을 때 한 번만. 선택 해제 등으로 배치만 바뀌면 화면은 그대로 둔다
  const handled = useRef(-1)
  useEffect(() => {
    if (handled.current === fitTarget.n) return
    // 처리 표시는 실제로 맞춘 뒤에 한다 (StrictMode 처럼 effect 가 취소되고 다시 돌아도 맞춤이 빠지지 않게)
    const id = requestAnimationFrame(() => {
      handled.current = fitTarget.n
      if (fitTarget.kind === 'all') {
        void fitView({ padding: 0.08, duration: 300 })
        return
      }
      if (fitTarget.kind === 'themes') {
        const ids = layout.nodes
          .filter((n) => n.kind === 'root' || n.kind === 'theme')
          .map((n) => ({ id: n.id }))
        void fitView({ nodes: ids, padding: 0.15, maxZoom: 1.2 })
        return
      }
      if (fitTarget.kind === 'concept') {
        const ids = new Set([fitTarget.id])
        for (const e of layout.edges) {
          if (e.kind === 'branch') continue
          if (e.source === fitTarget.id) ids.add(e.target)
          if (e.target === fitTarget.id) ids.add(e.source)
        }
        void fitView({
          nodes: [...ids].map((nid) => ({ id: nid })),
          padding: 0.2,
          maxZoom: 1.2,
          duration: 300,
        })
        return
      }
      const tid = themeId(fitTarget.theme)
      if (fitTarget.expanded) {
        const ids = layout.nodes
          .filter((n) => n.id === tid || (n.kind === 'concept' && n.node.theme === fitTarget.theme))
          .map((n) => ({ id: n.id }))
        void fitView({ nodes: ids, padding: 0.15, maxZoom: 1.2, duration: 300 })
      } else {
        const node = getNode(tid)
        if (node) {
          void setCenter(node.position.x + THEME_W / 2, node.position.y + THEME_H / 2, {
            zoom: getZoom(),
            duration: 300,
          })
        }
      }
    })
    return () => cancelAnimationFrame(id)
  }, [fitTarget, layout, fitView, setCenter, getZoom, getNode])

  const onNodeClick: NodeMouseHandler = (_, node) => {
    if (node.type === 'theme') {
      toggleTheme((node.data as { theme: string }).theme)
      setSelectedId(null)
    } else if (node.type === 'concept') {
      if (selectedId === node.id) {
        setSelectedId(null)
      } else {
        setSelectedId(node.id)
        nextFit({ kind: 'concept', id: node.id })
      }
    }
  }

  return (
    <div className="relative min-h-0 flex-1">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={() => setSelectedId(null)}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnDoubleClick={false}
        minZoom={0.2}
        maxZoom={2.5}
      >
        <Background variant={BackgroundVariant.Dots} gap={14} size={1} color="#cbd5e1" />
      </ReactFlow>

      <Legend />

      {/* 확대·축소·전체 보기 (시안 오른쪽 위) */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-2">
        <MapButton label="확대" onClick={() => void zoomIn({ duration: 200 })}>
          +
        </MapButton>
        <MapButton label="축소" onClick={() => void zoomOut({ duration: 200 })}>
          −
        </MapButton>
        <MapButton label="전체 보기" onClick={() => nextFit({ kind: 'all' })} small>
          전체
        </MapButton>
      </div>

      {selected ? (
        <ConceptPanel concept={selected} map={map} />
      ) : (
        <p className="pointer-events-none absolute inset-x-4 bottom-4 z-10 rounded-full bg-slate-800/90 px-4 py-2.5 text-center text-[11px] text-white">
          드래그로 이동 · 두 손가락이나 +/−로 확대 · 노드를 눌러보세요
        </p>
      )}
    </div>
  )
}

interface MapButtonProps {
  label: string
  onClick: () => void
  small?: boolean
  children: ReactNode
}

const MapButton = ({ label, onClick, small, children }: MapButtonProps) => (
  <button
    type="button"
    aria-label={label}
    onClick={onClick}
    className={`flex size-11 items-center justify-center rounded-xl border border-slate-200 bg-white font-semibold text-slate-800 shadow-sm ${
      small ? 'text-xs' : 'text-xl'
    }`}
  >
    {children}
  </button>
)

/** 범례 (시안 왼쪽 위) */
const Legend = () => {
  const lines = [
    { label: '올리는 힘', color: EDGE_COLORS.up },
    { label: '누르는 힘', color: EDGE_COLORS.down },
  ]
  return (
    <div className="pointer-events-none absolute top-3 left-3 z-10 space-y-1 rounded-xl border border-slate-200 bg-white/95 px-3 py-2 shadow-sm">
      {lines.map((l) => (
        <p key={l.label} className="flex items-center gap-2 text-[11px] text-slate-700">
          <svg width="18" height="6" aria-hidden>
            <line
              x1="1"
              y1="3"
              x2="17"
              y2="3"
              stroke={l.color}
              strokeWidth="3"
              strokeLinecap="round"
            />
          </svg>
          {l.label}
        </p>
      ))}
      <p className="flex items-center gap-2 text-[11px] text-slate-700">
        <span className="rounded-full bg-slate-700 px-1 text-[8px] leading-[14px] font-bold text-white">
          +N
        </span>
        누르면 보이는 연결
      </p>
    </div>
  )
}

interface ConceptPanelProps {
  concept: MapNode
  map: CausalMap
}

/** 개념을 누르면 아래에 뜨는 정보. 연결은 접기와 무관하게 원래 개념 기준으로 보여 준다 */
const ConceptPanel = ({ concept, map }: ConceptPanelProps) => {
  const byId = new Map(map.nodes.map((n) => [n.id, n]))
  const label = (id: string) => {
    const n = byId.get(id)
    if (!n) return id
    return n.learned ? n.name : `${n.name}(아직 안 배움)`
  }
  const out = map.edges.filter((e) => e.from === concept.id)
  const inc = map.edges.filter((e) => e.to === concept.id)
  const rows = [
    {
      title: '이 개념이 올림',
      color: EDGE_COLORS.up,
      items: out.filter((e) => e.forceDir === 'up').map((e) => label(e.to)),
    },
    {
      title: '이 개념이 누름',
      color: EDGE_COLORS.down,
      items: out.filter((e) => e.forceDir === 'down').map((e) => label(e.to)),
    },
    {
      title: '올려 주는 것',
      color: EDGE_COLORS.up,
      items: inc.filter((e) => e.forceDir === 'up').map((e) => label(e.from)),
    },
    {
      title: '눌러 주는 것',
      color: EDGE_COLORS.down,
      items: inc.filter((e) => e.forceDir === 'down').map((e) => label(e.from)),
    },
  ].filter((r) => r.items.length > 0)

  const percent = concept.total > 0 ? Math.round((concept.correct / concept.total) * 100) : null

  return (
    <div className="absolute inset-x-3 bottom-3 z-10 rounded-2xl border border-slate-200 bg-white p-3 shadow-lg">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-bold text-slate-900">{concept.name}</p>
        <p className="shrink-0 text-[11px] text-slate-500">
          {concept.theme} · 정답률 {percent ?? 0}%
        </p>
      </div>
      <dl className="mt-2 space-y-1">
        {rows.map((r) => (
          <div key={r.title} className="flex gap-2 text-[11px]">
            <dt className="w-20 shrink-0 font-medium" style={{ color: r.color }}>
              {r.title}
            </dt>
            <dd className="text-slate-800">{r.items.join(', ')}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
