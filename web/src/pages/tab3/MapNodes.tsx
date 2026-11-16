import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { REVIEW_COLOR } from '@/pages/tab3/mapColors'
import type { MapNode } from '@/types/causalMap'

/** 인과 지도 노드 3종 (디자인 시안): 뿌리 / 테마 / 개념. 연결은 왼쪽으로 들어와 오른쪽으로 나간다 */

/** 연결용 점. 사용자가 연결을 만들지 않으므로 보이지 않게 둔다 */
const HiddenHandles = () => (
  <>
    <Handle type="target" position={Position.Left} isConnectable={false} className="opacity-0" />
    <Handle type="source" position={Position.Right} isConnectable={false} className="opacity-0" />
  </>
)

export type RootFlowNode = Node<Record<string, never>, 'root'>

export const RootNode = () => (
  <div className="flex h-full w-full items-center justify-center rounded-lg bg-slate-900 text-[11px] font-bold text-white shadow-sm">
    <HiddenHandles />
    나의 인과 지도
  </div>
)

export type ThemeNodeData = { theme: string; color: string; collapsed: boolean; count: number }
export type ThemeFlowNode = Node<ThemeNodeData, 'theme'>

/** 테마 노드. 누르면 접고 편다 (클릭 처리는 CausalMapView 의 onNodeClick) */
export const ThemeNode = ({ data }: NodeProps<ThemeFlowNode>) => (
  <div
    className="flex h-full w-full items-center justify-center gap-1 rounded-full text-[11px] font-bold text-white shadow-sm"
    style={{ backgroundColor: data.color }}
    aria-expanded={!data.collapsed}
  >
    <HiddenHandles />
    {data.theme}
    {data.collapsed && (
      <span className="rounded-full bg-white/25 px-1.5 text-[9px] font-semibold">
        +{data.count}
      </span>
    )}
  </div>
)

export type ConceptNodeData = {
  node: MapNode
  review: boolean
  dim: boolean
  selected: boolean
}
export type ConceptFlowNode = Node<ConceptNodeData, 'concept'>

export const ConceptNode = ({ data }: NodeProps<ConceptFlowNode>) => {
  const { node, review, dim, selected } = data
  return (
    <div
      className={`relative flex h-full w-full items-center rounded-md border bg-white px-2 shadow-sm transition-opacity ${
        selected ? 'border-slate-900 ring-2 ring-slate-900/15' : 'border-slate-200'
      } ${dim ? 'opacity-25' : ''}`}
    >
      <HiddenHandles />
      {review && (
        <span
          aria-label="복습 필요"
          className="absolute -top-1 -left-1 size-2.5 rounded-full ring-2 ring-white"
          style={{ backgroundColor: REVIEW_COLOR }}
        />
      )}
      <p className="line-clamp-2 text-[10px] leading-tight font-medium text-slate-800">
        {node.name}
      </p>
    </div>
  )
}
