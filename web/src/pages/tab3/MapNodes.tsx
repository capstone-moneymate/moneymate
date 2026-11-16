import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import type { Side } from '@/pages/tab3/causalMapLayout'
import type { MapNode } from '@/types/causalMap'

/**
 * 인과 지도 노드 4종: 뿌리 / 테마 / 개념 / 임시 이웃(ghost).
 * 마인드맵이라 오른쪽 가지는 왼쪽으로 들어와 오른쪽으로 나가고, 왼쪽 가지는 거꾸로다.
 */

/** 연결용 점. 사용자가 연결을 만들지 않으므로 보이지 않게 둔다 */
const SideHandles = ({ side }: { side: Side }) => (
  <>
    <Handle
      type="target"
      position={side === 'right' ? Position.Left : Position.Right}
      isConnectable={false}
      className="opacity-0"
    />
    <Handle
      type="source"
      position={side === 'right' ? Position.Right : Position.Left}
      isConnectable={false}
      className="opacity-0"
    />
  </>
)

export type RootFlowNode = Node<Record<string, never>, 'root'>

/** 뿌리는 양쪽으로 가지가 나간다 (id: left / right) */
export const RootNode = () => (
  <div className="flex h-full w-full items-center justify-center rounded-lg bg-slate-900 text-[11px] font-bold text-white shadow-sm">
    <Handle
      id="left"
      type="source"
      position={Position.Left}
      isConnectable={false}
      className="opacity-0"
    />
    <Handle
      id="right"
      type="source"
      position={Position.Right}
      isConnectable={false}
      className="opacity-0"
    />
    나의 인과 지도
  </div>
)

export type ThemeNodeData = {
  side: Side
  theme: string
  color: string
  collapsed: boolean
  count: number
}
export type ThemeFlowNode = Node<ThemeNodeData, 'theme'>

/** 테마 노드. 누르면 접고 편다 (클릭 처리는 CausalMapView 의 onNodeClick) */
export const ThemeNode = ({ data }: NodeProps<ThemeFlowNode>) => (
  <div
    className="flex h-full w-full items-center justify-center gap-1 rounded-full text-[11px] font-bold text-white shadow-sm"
    style={{ backgroundColor: data.color }}
    aria-expanded={!data.collapsed}
  >
    <SideHandles side={data.side} />
    {data.theme}
    {data.collapsed && (
      <span className="rounded-full bg-white/25 px-1.5 text-[9px] font-semibold">
        +{data.count}
      </span>
    )}
  </div>
)

export type ConceptNodeData = {
  side: Side
  node: MapNode
  /** 처음 화면에 안 그린 연결 수. 누르면 보인다 */
  hidden: number
  dim: boolean
  selected: boolean
}
export type ConceptFlowNode = Node<ConceptNodeData, 'concept'>

export const ConceptNode = ({ data }: NodeProps<ConceptFlowNode>) => {
  const { side, node, hidden, dim, selected } = data
  return (
    <div
      className={`relative flex h-full w-full items-center rounded-md border bg-white px-2 shadow-sm transition-opacity ${
        selected ? 'border-slate-900 ring-2 ring-slate-900/15' : 'border-slate-200'
      } ${dim ? 'opacity-25' : ''}`}
    >
      <SideHandles side={side} />
      <p className="line-clamp-2 text-[10px] leading-tight font-medium text-slate-800">
        {node.name}
      </p>
      {hidden > 0 && !selected && (
        <span
          aria-label={`누르면 보이는 연결 ${hidden}개`}
          className={`absolute -top-1.5 rounded-full bg-slate-700 px-1 text-[8px] leading-[14px] font-bold text-white ring-2 ring-white ${
            side === 'right' ? '-right-1.5' : '-left-1.5'
          }`}
        >
          +{hidden}
        </span>
      )}
    </div>
  )
}

export type GhostNodeData = { side: Side; node: MapNode }
export type GhostFlowNode = Node<GhostNodeData, 'ghost'>

/** 고른 개념 옆에 잠깐 놓는 이웃. 아직 안 배운 개념은 점선, 접힌 테마의 배운 개념은 실선 */
export const GhostNode = ({ data }: NodeProps<GhostFlowNode>) => (
  <div
    className={`relative flex h-full w-full items-center rounded-md border px-2 shadow-md ${
      data.node.learned ? 'border-slate-300 bg-white' : 'border-dashed border-slate-400 bg-slate-50'
    }`}
  >
    <SideHandles side={data.side} />
    <p
      className={`line-clamp-2 text-[10px] leading-tight font-medium ${
        data.node.learned ? 'text-slate-800' : 'text-slate-500'
      }`}
    >
      {data.node.name}
    </p>
  </div>
)
