/**
 * 탭2 안내 문구. 화면에 나가는 안내·대체 문구는 이 파일 한 곳에서만 고친다.
 * 문구는 화면 시안(18~25, 머니메이트_전체흐름_화면별)을 따르고, 시안에 없는 빈 상태 문구만 따로 썼다.
 * 매수·매도 권유나 앞으로의 주가를 말하는 표현은 쓰지 않는다 (CLAUDE.md 10).
 */

/** 13F 공시 목록 아래 (시안 18) */
export const F13_NOTE = "따라 사기 위한 목록이 아니라, 큰손이 '왜 샀을까'를 읽어보는 기록이에요."

/** 액티브 ETF 목록 아래 (시안 22). 수량이 1CU 기준이라 비중이 아니라 수량으로 보여 준다 */
export const ETF_NOTE = '주가만 올라도 커지는 비중 대신, 실제로 사고판 수량으로 보여줘요.'

/** 종목 상세 버튼 아래 고정 안내 (시안 19~25) */
export const DETAIL_NOTE =
  '매니저는 매매 이유를 공개하지 않아요. 뉴스를 바탕으로 한 추정이고, 따라 사기 위한 정보가 아니에요'

/** 큰손 2명 이상이 함께 담은 종목이 없을 때 (#164 부터 방향과 상관없이 보유 기준) */
export const NO_OVERLAP_NOTE = (min: number) =>
  `이번 분기에는 큰손 ${min}명 이상이 함께 담은 종목이 없어요.`

/** 카드 ① 어제 움직임이 분기 말 이후 추세와 반대일 때 (시안 19 "추세와 반대로 움직였어요 · 왜?") */
export const AGAINST_TREND_TITLE = '추세와 반대로 움직였어요 · 왜?'
export const AGAINST_TREND_TEXT =
  '하루 움직임은 한 종목 비중이 너무 커지지 않게 덜어 내는 조절일 수 있어요. 전망이 나빠져서 판 것과는 달라요.'

/** 카드 ② 아래 (시안 20). 날짜는 13F 분기 말 */
export const reasonsFootNote = (periodEnd: string) =>
  `파란 칸은 내 인과 지도에 있는 노드예요 · 13F 이유는 ${periodEnd} 이전 뉴스만 근거로 써요`

/**
 * 카드 ② 양쪽 이유 (큰손과 ETF 가 반대로 움직인 종목, 2026-11-19 B). 13F 는 분기 말 기록, ETF 추세는 그 뒤라
 * 기간마다 따로 설명한다. 날짜는 '9/30' 형식
 */
export const sideTitle = (side: 'big' | 'etf', periodEnd: string, etfUntil: string | null) =>
  side === 'big'
    ? `큰손 쪽 · ${periodEnd}까지 기록`
    : `ETF 쪽 · ${periodEnd} 이후${etfUntil ? ` ~ ${etfUntil}` : ''} 추세`

/** 양쪽 이유인데 한쪽 이유가 없을 때 (그 기간 근거가 없거나 검사에서 버려짐) */
export const SIDE_MISSING_TEXT = '이 기간 자료로는 설명할 이유를 찾지 못했어요.'

/** 양쪽 이유 카드 아래 */
export const splitFootNote = (periodEnd: string) =>
  `파란 칸은 내 인과 지도에 있는 노드예요 · 큰손 이유는 ${periodEnd} 이전, ETF 이유는 그 뒤 자료만 근거로 써요`

/** 카드 ② 이유가 아직 없을 때 */
export const NO_REASONS_TEXT =
  '이 종목의 이유 카드는 아직 준비되지 않았어요. 앞 카드에서 무엇이 바뀌었는지 먼저 살펴보세요.'

/**
 * 카드 ② 이유를 만들었지만 검사에서 전부 버려졌을 때 (서버 reasonsRejected, #164).
 * 방향이 큰손 변화와 맞는 이유가 없어서 억지로 지어내지 않고 고정 문구로 둔다 (C #161).
 */
export const REJECTED_REASONS_TEXT = '공개된 자료로는 설명할 이유를 찾지 못했어요.'

/** 카드 ③ 이 아직 없을 때 */
export const NO_NOW_TEXT = '지금은 카드가 아직 준비되지 않았어요.'

/** 카드 ③ 오늘 탭 1 에서 다룬 개념과 이어질 때 (시안 21) */
export const NOW_LINKED_TITLE = '오늘 배운 뉴스랑 연결돼요'

/** "내 지도에 있어요" 배지 (시안 20). 경로에 배운 개념이 있을 때 */
export const MY_MAP_BADGE = '내 지도에 있어요'

/** 경로에 배운 개념이 하나도 없을 때 (시안 20 "새 뼈대") */
export const NEW_SKELETON_BADGE = '새 뼈대'
