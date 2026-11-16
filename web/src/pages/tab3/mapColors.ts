import type { LayoutEdgeDir } from '@/pages/tab3/causalMapLayout'

/**
 * 인과 지도 색 (디자인 시안 기준).
 * 연결: 올리는 힘 빨강, 누르는 힘 파랑. 탭 2의 늘림▲·줄임▼와 같은 색이라 ▲▼ 기호는 붙이지 않고 범례로만 설명한다.
 */
export const EDGE_COLORS: Record<LayoutEdgeDir, string> = {
  up: '#d6213b',
  down: '#1b64da',
  /** 접어서 올림·누름이 섞인 연결 */
  mixed: '#94a3b8',
}

/** 복습 필요 점 */
export const REVIEW_COLOR = '#e11d48'

/** 테마 색. 시안의 금리·AI·반도체·차트 읽기 색을 따르고, 나머지는 순서대로 */
const THEME_COLORS: Record<string, string> = {
  금리: '#2563eb',
  'AI·반도체': '#be123c',
  '차트 읽기': '#047857',
}
const EXTRA_COLORS = ['#7c3aed', '#b45309', '#0e7490', '#4d7c0f', '#9d174d']

export const themeColor = (theme: string, index: number) =>
  THEME_COLORS[theme] ?? EXTRA_COLORS[index % EXTRA_COLORS.length]
