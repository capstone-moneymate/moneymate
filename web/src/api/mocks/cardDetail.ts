import type { CardDetail } from '@/types/card'

/**
 * 탭1 카드뉴스·단계 목 데이터. 자료·수치는 프로토타입 예시이고, 카드 API 연결 후 삭제한다.
 * 카드 id는 newsHome 목 데이터와 같다. 개념 id는 db/seeds/concepts.csv 에 있는 것만 쓴다.
 */
export const cardDetailMocks: Record<string, CardDetail> = {
  'mock-rate-hold': {
    id: 'mock-rate-hold',
    type: 2,
    title: '한국은행, 기준금리 4연속 동결',
    theme: '금리',
    sourceName: '한국은행',
    sourceUrl: 'https://www.bok.or.kr/',
    sourcePublishedAt: '2026-10-08T01:30:00Z',
    ticker: null,
    slides: [
      {
        label: '무슨 일이 있었나요?',
        heading: '기준금리를 이번에도 그대로 뒀어요',
        body: '한국은행 금융통화위원회가 기준금리를 바꾸지 않기로 했어요. 물가와 가계부채를 함께 살폈다고 밝혔어요.',
        facts: [{ label: '기준금리', value: '3.00% (동결)' }],
      },
      {
        label: '시장이 주목한 포인트',
        heading: '은행주와 기술주가 다르게 움직였어요',
        body: '금리가 높은 수준에 머물면 은행은 이자로 버는 돈이 유지되고, 미래 이익을 보고 사는 성장주는 부담이 남아요.',
        facts: [
          { label: '은행 업종', value: '▲ 1.8%' },
          { label: '기술주 ETF', value: '▼ 0.6%' },
        ],
      },
      {
        label: '오늘의 결론',
        heading: '같은 소식도 업종마다 미는 방향이 달라요',
        body: '금리 동결이라는 한 사건이 어떤 업종은 올리고 어떤 업종은 누르는 힘이 될 수 있어요. 인과 순서로 정리해 봐요.',
      },
    ],
    steps: [
      {
        id: 'rh-1',
        no: 1,
        kind: 'concept',
        conceptIds: ['rate_hold', 'growth_valuation'],
        title: '기준금리와 성장주',
        body: '기준금리는 시장 금리의 출발점이에요. 금리가 높게 유지되면 먼 미래의 이익을 오늘 가치로 바꿀 때 더 많이 깎여서, 성장주의 가치평가가 낮아지기 쉬워요.',
        terms: [
          { term: '기준금리 동결', desc: '한국은행이 정책금리를 바꾸지 않고 그대로 두는 것' },
          { term: '성장주', desc: '지금 이익보다 앞으로 커질 이익을 기대받는 회사의 주식' },
        ],
      },
      {
        id: 'rh-2',
        no: 2,
        kind: 'quiz',
        conceptIds: ['rate_hold'],
        question: '기준금리 "동결"은 무슨 뜻일까요?',
        options: ['금리를 올렸다', '금리를 내렸다', '금리를 그대로 뒀다', '금리를 없앴다'],
      },
      {
        id: 'rh-3',
        no: 3,
        kind: 'causal_order',
        conceptIds: ['rate_hold', 'bond_yield', 'growth_valuation'],
        question: '금리 동결이 성장주에 닿기까지, 힘이 전해지는 순서대로 눌러 보세요.',
        items: [
          { conceptId: 'growth_valuation', label: '성장주 가치평가 부담' },
          { conceptId: 'rate_hold', label: '기준금리 동결' },
          { conceptId: 'bond_yield', label: '시장금리 높게 유지' },
        ],
      },
      {
        id: 'rh-4',
        no: 4,
        kind: 'chart',
        conceptIds: ['volume_spike'],
        question: '발표 날 은행 업종 거래량은 평소와 비교해 어땠을까요?',
        ticker: 'KS11',
        options: ['평소보다 많았다', '평소와 비슷했다', '평소보다 적었다'],
      },
      {
        id: 'rh-5',
        no: 5,
        kind: 'judgement',
        conceptIds: ['rate_hold', 'bank_margin', 'growth_valuation'],
        question: '금리 동결 뒤, 다음 주에 어느 쪽 흐름을 더 지켜볼지 고르고 근거를 써 보세요.',
        context: '가상의 판단 연습이에요. 고른 답은 채점하지 않고, 근거를 얼마나 잘 썼는지만 봐요.',
        choices: ['은행주 흐름을 더 지켜본다', '기술주 흐름을 더 지켜본다', '둘 다 지켜본다'],
      },
    ],
  },
  'mock-hbm4': {
    id: 'mock-hbm4',
    type: 3,
    title: 'SK하이닉스, HBM 단일판매·공급계약 체결',
    theme: 'AI·반도체',
    sourceName: 'DART · SK하이닉스',
    sourceUrl: 'https://dart.fss.or.kr/',
    sourcePublishedAt: '2026-10-08T07:40:00Z',
    ticker: 'NVDA',
    slides: [
      {
        label: '무슨 일이 있었나요?',
        heading: 'AI 칩용 메모리 공급 계약을 공시했어요',
        body: 'SK하이닉스가 고대역폭메모리(HBM) 단일판매·공급계약을 DART에 공시했어요. 매출액 대비 큰 규모라 의무 공시 대상이에요.',
      },
      {
        label: '시장이 주목한 포인트',
        heading: 'HBM은 AI 칩 옆에 붙는 메모리예요',
        body: 'AI 칩(GPU)이 많이 팔릴수록 HBM도 많이 필요해요. 그래서 이 계약은 AI 칩 수요가 이어진다는 신호로 읽혔어요.',
      },
    ],
    steps: [
      {
        id: 'hb-1',
        no: 1,
        kind: 'concept',
        conceptIds: ['hbm_supply', 'gpu_demand'],
        title: 'HBM, 액티브 ETF, 보유 수량 읽기',
        body: '액티브 ETF는 매니저가 종목과 수량을 직접 바꾸는 ETF예요. 보유 수량이 늘었다면 매니저가 그 종목을 더 담았다는 뜻이에요.',
        terms: [
          { term: 'HBM', desc: 'AI 칩 옆에 쌓아 붙이는 빠른 메모리' },
          { term: '액티브 ETF', desc: '지수를 그대로 따르지 않고 매니저가 종목을 고르는 ETF' },
          { term: '보유 수량', desc: '주식을 몇 주 갖고 있는지. 주가가 올라도 수량은 그대로예요' },
        ],
      },
      {
        id: 'hb-2',
        no: 2,
        kind: 'open_ended',
        conceptIds: ['hbm_supply', 'gpu_demand', 'ai_investment'],
        question: 'KoAct가 엔비디아(NVDA)를 왜 늘렸을까요? 오늘 공시와 이어서 써 보세요.',
        context: 'KoAct 미국나스닥성장기업액티브는 9/30 이후 NVDA 보유 수량을 늘렸어요.',
      },
      { id: 'hb-3', no: 3, kind: 'ai_analysis', conceptIds: [] },
    ],
  },
  'mock-kospi-3up': {
    id: 'mock-kospi-3up',
    type: 1,
    title: '코스피, 3거래일 연속 상승 마감',
    theme: '차트 읽기',
    sourceName: 'KRX 시세',
    sourceUrl: 'https://data.krx.co.kr/',
    sourcePublishedAt: '2026-10-08T06:30:00Z',
    ticker: null,
    slides: [
      {
        label: '무슨 일이 있었나요?',
        heading: '코스피가 사흘째 올랐어요',
        body: '코스피 지수가 3거래일 연속으로 전날보다 높게 마감했어요.',
        facts: [{ label: '3일 수익률', value: '▲ 2.4%' }],
      },
      {
        label: '오늘의 결론',
        heading: '오른 날, 거래량도 같이 늘었을까요?',
        body: '가격만 보지 말고 거래량을 같이 보면 얼마나 많은 사람이 참여했는지 알 수 있어요.',
      },
    ],
    steps: [
      {
        id: 'kp-1',
        no: 1,
        kind: 'concept',
        conceptIds: ['consecutive_rise', 'volume_spike'],
        title: '연속 상승과 거래량',
        body: '연속 상승은 며칠 이어서 종가가 전날보다 높았다는 뜻이에요. 이때 거래량이 함께 늘었다면 많은 사람이 그 움직임에 참여했다는 신호예요.',
        terms: [
          { term: '연속 상승', desc: '종가가 여러 거래일 이어서 전날보다 높게 끝난 것' },
          { term: '거래량', desc: '그날 사고팔린 주식 수' },
        ],
      },
      {
        id: 'kp-2',
        no: 2,
        kind: 'quiz',
        conceptIds: ['consecutive_rise'],
        question: '"3거래일 연속 상승"을 바르게 설명한 것은?',
        options: [
          '3일 동안 장중에 한 번이라도 올랐다',
          '3거래일 동안 종가가 전날보다 높게 끝났다',
          '3일 전보다 지금 가격이 높다',
        ],
      },
      {
        id: 'kp-3',
        no: 3,
        kind: 'chart',
        conceptIds: ['volume_spike'],
        question: '3일 중 거래량이 가장 많았던 날은 언제일까요?',
        ticker: 'KS11',
        options: ['첫째 날', '둘째 날', '셋째 날'],
      },
      {
        id: 'kp-4',
        no: 4,
        kind: 'judgement',
        conceptIds: ['consecutive_rise', 'volume_spike'],
        question:
          '연속 상승 다음 날, 거래량을 보고 어떤 점을 확인하겠어요? 하나 고르고 근거를 써 보세요.',
        context: '가상의 판단 연습이에요. 고른 답은 채점하지 않고, 근거를 얼마나 잘 썼는지만 봐요.',
        choices: [
          '거래량이 이어지는지 본다',
          '거래량이 줄어드는지 본다',
          '거래량보다 다른 지표를 본다',
        ],
      },
    ],
  },
}

/**
 * 목 채점에 쓰는 정답 (서버 steps.answer 자리). 화면 코드는 이걸 직접 읽지 않고 api/cards.ts 만 쓴다.
 * quiz·chart: 보기 번호, causal_order: 개념 id 순서
 */
export const answerMocks: Record<string, { correct: number | string[]; explanation: string }> = {
  'rh-2': {
    correct: 2,
    explanation: '동결은 금리를 올리지도 내리지도 않고 그대로 둔다는 뜻이에요.',
  },
  'rh-3': {
    correct: ['rate_hold', 'bond_yield', 'growth_valuation'],
    explanation:
      '기준금리가 그대로면 시장금리도 높게 유지되고, 그만큼 성장주의 미래 이익이 덜 매력적으로 계산돼요.',
  },
  'rh-4': { correct: 0, explanation: '발표 날 은행 업종 거래량은 252일 평균보다 많았어요.' },
  'kp-2': {
    correct: 1,
    explanation: '연속 상승은 종가 기준이에요. 장중에 올랐다가 내려서 끝나면 상승으로 세지 않아요.',
  },
  'kp-3': {
    correct: 2,
    explanation: '셋째 날 거래량이 가장 많았어요. 상승에 참여한 사람이 늘었다는 뜻이에요.',
  },
}
