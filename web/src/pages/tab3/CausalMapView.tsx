import { useEffect, useMemo, useState, type ReactNode } from 'react'
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
  needsReview,
  NODE_H,
  NODE_W,
  ROOT_H,
  ROOT_W,
  THEME_H,
  THEME_W,
  themeId,
  themesOf,
} from '@/pages/tab3/causalMapLayout'
import { EDGE_COLORS, REVIEW_COLOR, themeColor } from '@/pages/tab3/mapColors'
import { ConceptNode, RootNode, ThemeNode } from '@/pages/tab3/MapNodes'
import type { CausalMap, MapNode } from '@/types/causalMap'

const nodeTypes = { root: RootNode, theme: ThemeNode, concept: ConceptNode }

/** 접기·펼치기 뒤 화면을 어디에 맞출지 */
type FitTarget = { kind: 'all' } | { kind: 'theme'; theme: string; expanded: boolean }

interface CausalMapViewProps {
  map: CausalMap
}

/**
 * 인과 지도 (React Flow, 디자인 시안의 가로 나무 모양).
 * 테마 노드를 누르면 접고 펴고, 개념을 누르면 연결된 것만 진하게 하고 아래에 정보를 보여 준다.
 */
export const CausalMapView = ({ map }: CausalMapViewProps) => {
  const themes = useMemo(() => themesOf(map), [map])
  const colors = useMemo(() => new Map(themes.map((t, i) => [t, themeColor(t, i)])), [themes])
  const [collapsed, setCollapsed] = useState<ReadonlySet<string>>(() => new Set())
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [fitTarget, setFitTarget] = useState<FitTarget>({ kind: 'all' })
  const { fitView, setCenter, getZoom, getNode, zoomIn, zoomOut } = useReactFlow()

  const layout = useMemo(() => buildLayout(map, collapsed), [map, collapsed])

  // 선택한 개념이 접혀 사라지면 선택을 지운다 (렌더 중 판정, effect 불필요)
  const selected =
    selectedId && layout.nodes.some((n) => n.id === selectedId)
      ? (map.nodes.find((n) => n.id === selectedId) ?? null)
      : null

  /** 선택한 개념과 바로 이어진 노드 (나머지는 흐리게) */
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

  const toggleTheme = (theme: string) => {
    const expanding = collapsed.has(theme)
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (expanding) next.delete(theme)
      else next.add(theme)
      return next
    })
    setFitTarget({ kind: 'theme', theme, expanded: expanding })
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
              data: {
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
                node: n.node,
                review: needsReview(n.node),
                dim,
                selected: n.id === selectedId,
              },
            }
        }
      }),
    [layout, neighbors, selectedId, colors],
  )

  const edges: Edge[] = useMemo(
    () =>
      layout.edges.map((e): Edge => {
        const base = { id: e.id, source: e.source, target: e.target }
        if (e.kind === 'branch') {
          return {
            ...base,
            style: {
              stroke: colors.get(e.theme),
              strokeWidth: 2,
              opacity: selected ? 0.15 : 0.55,
            },
          }
        }
        const touches = selected !== null && (e.source === selected.id || e.target === selected.id)
        const opacity = selected && !touches ? 0.1 : 1
        const color = EDGE_COLORS[e.dir]
        return {
          ...base,
          style: {
            stroke: color,
            strokeWidth: e.count > 1 ? 2.4 : 1.5,
            strokeDasharray: e.dir === 'mixed' ? '2 3' : undefined,
            opacity,
          },
          markerEnd: { type: MarkerType.ArrowClosed, color, width: 12, height: 12 },
        }
      }),
    [layout, selected, colors],
  )

  // 접기·펼치기 뒤 새 배치가 그려진 다음 화면을 맞춘다
  useEffect(() => {
    const id = requestAnimationFrame(() => {
      if (fitTarget.kind === 'all') {
        void fitView({ padding: 0.08, duration: 300 })
        return
      }
      const tid = themeId(fitTarget.theme)
      if (fitTarget.expanded) {
        // 편 테마와 그 개념들로 맞춘다
        const ids = [tid, ...map.nodes.filter((n) => n.theme === fitTarget.theme).map((n) => n.id)]
        void fitView({
          nodes: ids.map((nid) => ({ id: nid })),
          padding: 0.15,
          maxZoom: 1.2,
          duration: 300,
        })
      } else {
        // 접은 테마 노드를 화면 가운데로 (배율 유지)
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
  }, [layout, fitTarget, fitView, setCenter, getZoom, getNode, map])

  const onNodeClick: NodeMouseHandler = (_, node) => {
    if (node.type === 'theme') {
      toggleTheme((node.data as { theme: string }).theme)
      setSelectedId(null)
    } else if (node.type === 'concept') {
      setSelectedId((prev) => (prev === node.id ? null : node.id))
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
        fitView
        fitViewOptions={{ padding: 0.08 }}
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
        <MapButton label="전체 보기" onClick={() => setFitTarget({ kind: 'all' })} small>
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
        <span className="mx-1 size-2.5 rounded-full" style={{ backgroundColor: REVIEW_COLOR }} />
        복습 필요
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
  const nameOf = (id: string) => map.nodes.find((n) => n.id === id)?.name ?? id
  const out = map.edges.filter((e) => e.from === concept.id)
  const inc = map.edges.filter((e) => e.to === concept.id)
  const rows = [
    {
      title: '이 개념이 올림',
      color: EDGE_COLORS.up,
      items: out.filter((e) => e.forceDir === 'up').map((e) => nameOf(e.to)),
    },
    {
      title: '이 개념이 누름',
      color: EDGE_COLORS.down,
      items: out.filter((e) => e.forceDir === 'down').map((e) => nameOf(e.to)),
    },
    {
      title: '올려 주는 것',
      color: EDGE_COLORS.up,
      items: inc.filter((e) => e.forceDir === 'up').map((e) => nameOf(e.from)),
    },
    {
      title: '눌러 주는 것',
      color: EDGE_COLORS.down,
      items: inc.filter((e) => e.forceDir === 'down').map((e) => nameOf(e.from)),
    },
  ].filter((r) => r.items.length > 0)

  return (
    <div className="absolute inset-x-3 bottom-3 z-10 rounded-2xl border border-slate-200 bg-white p-3 shadow-lg">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-bold text-slate-900">{concept.name}</p>
        <p className="shrink-0 text-[11px] text-slate-500">
          {concept.theme} · 정답 {concept.correct}/{concept.total}
          {needsReview(concept) && (
            <span className="ml-1 font-semibold" style={{ color: REVIEW_COLOR }}>
              복습 필요
            </span>
          )}
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
