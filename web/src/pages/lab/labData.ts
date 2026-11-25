/**
 * 분석 자료 탭의 내용 (UI 시안 docs/design/app.html 의 TOPICS·RECS 를 옮긴 것).
 * 서버에서 받지 않고 화면에 들어 있는 고정 내용이다.
 * - TOPICS: 자료 종류 여섯 가지의 기초 설명과 퀴즈 (일반 지식)
 * - RECS: "큰손 기록으로 풀어보기". 문제에 나오는 종목·인물·숫자는 읽는 법을 익히기 위한 **학습용 예시**이고
 *   실제 공시를 수집한 값이 아니다. 화면에도 예시라고 적는다. 실제 값으로 바꾸려면 탭2 겹침 데이터(/api/overlaps)로 만든다.
 */

export type LabQuiz =
  | {
      kind: 'mcq'
      hint: string
      q: string
      /** 문제 위 회색 칸: [작은 제목, 내용] */
      ctx?: [string, string]
      o: string[]
      a: number
      e: string
    }
  | { kind: 'ox'; hint: string; q: string; s: string; a: 'o' | 'x'; e: string }
  | {
      kind: 'blank'
      hint: string
      q: string
      pre: string
      post: string
      o: string[]
      a: number
      e: string
    }
  /** l[i] 의 짝은 r[i] */
  | { kind: 'match'; hint: string; q: string; l: string[]; r: string[]; e: string }
  /** s 가 정답 순서 */
  | { kind: 'order'; hint: string; q: string; s: string[]; e: string }

export interface LabTopic {
  id: string
  cat: string
  badge: string
  /** 배지 바탕색 (styles/index.css 의 색 이름) */
  color: string
  name: string
  /** 개념 칸의 큰 글자. 없으면 name */
  kw?: string
  sub: string
  /** 한 줄 정의 */
  d: string
  /** 덧붙이는 설명 */
  p: string[]
  quiz: LabQuiz
}

export interface LabRec {
  id: string
  cat: string
  kick: string
  title: string
  /** 문제 종류 이름 (칩에 보인다) */
  type: string
  quiz: LabQuiz
}

export const LAB_CATS = [
  '전체',
  '13F',
  '액티브 ETF',
  '내부자 거래',
  '실적 발표',
  '사업보고서',
  '애널리스트',
]

export const LAB_TOPICS: LabTopic[] = [
  {
    id: 'a13f',
    cat: '13F',
    badge: '13F',
    color: 'var(--color-blue-soft)',
    name: '13F 보고서',
    sub: '큰손은 무엇을 들고 있을까',
    d: '큰 기관투자자가 분기마다 보유 종목을 공개하는 보고서예요.',
    p: [
      '운용자산 1억 달러 이상인 기관이 미국 SEC에 내요.',
      '분기가 끝나고 45일 안에 공개돼요. 그래서 조금 늦은 정보예요.',
    ],
    quiz: {
      kind: 'mcq',
      hint: '객관식 · 하나만 골라요',
      q: '13F 보고서란 무엇일까요?',
      o: [
        '큰 기관투자자가 분기마다 보유 종목을 공개하는 보고서',
        '기업이 분기 실적을 발표하는 보고서',
        'ETF가 매일 공개하는 구성 종목 목록',
      ],
      a: 0,
      e: '운용자산 1억 달러 이상인 기관이 분기마다 미국 SEC에 내요. 분기가 끝나고 45일 안에 공개돼요.',
    },
  },
  {
    id: 'aetf',
    cat: '액티브 ETF',
    badge: 'ETF',
    color: 'var(--color-up-soft)',
    name: '액티브 ETF',
    sub: '매일 공개되는 운용 기록',
    d: '매니저가 종목을 직접 골라 담는 ETF예요.',
    p: [
      '지수를 그대로 따라가는 패시브 ETF와 달라요.',
      '보유 종목이 매일 공개돼서 매니저의 최근 움직임을 볼 수 있어요.',
    ],
    quiz: {
      kind: 'ox',
      hint: 'O/X · 맞으면 O, 틀리면 X',
      q: '맞는 말일까요?',
      s: '액티브 ETF는 지수를 그대로 따라가도록 만든 ETF다.',
      a: 'x',
      e: '지수를 그대로 따라가는 건 패시브 ETF예요. 액티브 ETF는 매니저가 종목과 비중을 직접 정해요.',
    },
  },
  {
    id: 'ains',
    cat: '내부자 거래',
    badge: 'Form 4',
    color: 'var(--color-butter-soft)',
    name: '내부자 거래 공시',
    sub: '임원은 자기 회사 주식을 샀을까',
    d: '임원이나 대주주가 자기 회사 주식을 사고판 기록이에요.',
    p: [
      '미국에서는 거래 후 2영업일 안에 SEC에 알려야 해요(Form 4).',
      '회사를 가장 잘 아는 사람들의 움직임이라 참고해요.',
    ],
    quiz: {
      kind: 'blank',
      hint: '빈칸 채우기 · 알맞은 말을 골라요',
      q: '빈칸에 들어갈 말은?',
      pre: '내부자 거래 공시는 회사',
      post: '가 자기 회사 주식을 사고판 기록이에요.',
      o: ['임원·대주주', '애널리스트', '개인 투자자'],
      a: 0,
      e: '회사 안쪽 사정을 아는 임원과 대주주의 거래예요. 미국에서는 거래 후 2영업일 안에 공개돼요.',
    },
  },
  {
    id: 'aern',
    cat: '실적 발표',
    badge: '실적',
    color: 'var(--color-ok-soft)',
    name: '실적 발표',
    sub: '얼마나 벌었는지 알리는 날',
    d: '회사가 분기마다 얼마나 벌었는지 알리는 발표예요.',
    p: [
      '매출·이익이 시장 예상보다 좋으면 ‘어닝 서프라이즈’라고 해요.',
      '숫자만큼, 다음 분기 전망(가이던스)에도 주가가 크게 반응해요.',
    ],
    quiz: {
      kind: 'mcq',
      hint: '객관식 · 하나만 골라요',
      q: '실적이 시장 예상보다 좋게 나온 걸 뭐라고 할까요?',
      o: ['어닝 서프라이즈', '어닝 쇼크', '가이던스'],
      a: 0,
      e: '예상보다 좋으면 어닝 서프라이즈, 예상보다 나쁘면 어닝 쇼크예요. 가이던스는 회사가 내놓는 앞으로의 전망이에요.',
    },
  },
  {
    id: 'a10k',
    cat: '사업보고서',
    badge: '10-K',
    color: 'var(--color-blue-soft)',
    name: '사업보고서',
    kw: '사업보고서 (10-K)',
    sub: '회사를 통째로 설명한 문서',
    d: '회사가 1년에 한 번 내는 종합 보고서예요.',
    p: [
      '어떤 사업을 하는지, 어떤 위험이 있는지, 재무제표까지 들어 있어요.',
      '분기마다 내는 보고서는 10-Q라고 해요.',
    ],
    quiz: {
      kind: 'match',
      hint: '짝 맞추기 · 왼쪽과 오른쪽을 이어요',
      q: '이름과 설명을 짝지어 보세요.',
      l: ['10-K', '10-Q', '13F'],
      r: ['1년에 한 번 내는 종합 보고서', '분기마다 내는 보고서', '기관의 보유 종목 보고서'],
      e: 'K는 1년에 한 번, Q는 분기(Quarter)마다예요. 13F는 회사가 아니라 기관투자자가 내는 보고서예요.',
    },
  },
  {
    id: 'aana',
    cat: '애널리스트',
    badge: '리포트',
    color: 'var(--color-up-soft)',
    name: '애널리스트 리포트',
    sub: '전문가의 의견 읽는 법',
    d: '증권사 애널리스트가 기업을 분석해서 쓴 의견이에요.',
    p: [
      '투자의견(매수·중립·매도)과 목표주가가 들어 있어요.',
      '사실이 아니라 ‘의견’이에요. 근거를 같이 읽어야 해요.',
    ],
    quiz: {
      kind: 'ox',
      hint: 'O/X · 맞으면 O, 틀리면 X',
      q: '맞는 말일까요?',
      s: '목표주가는 주가가 반드시 그 가격까지 간다는 뜻이다.',
      a: 'x',
      e: '목표주가는 애널리스트의 예상이에요. 틀릴 수 있어서 어떤 근거로 계산했는지 같이 봐야 해요.',
    },
  },
]

export const LAB_RECS: LabRec[] = [
  {
    id: 'r1',
    cat: '13F',
    kick: '13F 읽기 · 예시',
    title: '큰손들이 함께 늘린 종목은 무엇일까요?',
    type: '객관식',
    quiz: {
      kind: 'mcq',
      hint: '13F 읽기 · 학습용 예시',
      q: '큰손 3명이 함께 늘린 종목은 무엇일까요?',
      ctx: [
        '13F 공시 · 9/30 기준 (예시)',
        'NVDA 3명 · GOOGL 2명 · 4명 중 2명 이상이 늘린 종목만 보여요.',
      ],
      o: ['NVDA 엔비디아', 'GOOGL 알파벳', 'AAPL 애플'],
      a: 0,
      e: '표에서 가장 많은 사람이 늘린 종목을 찾으면 돼요. 이 예시에서는 3명이 늘린 엔비디아예요. 알파벳은 2명이 늘렸어요.',
    },
  },
  {
    id: 'r2',
    cat: '13F',
    kick: '13F 읽기 · 예시',
    title: '큰손은 왜 엔비디아를 늘렸을까요?',
    type: '순서 맞추기',
    quiz: {
      kind: 'order',
      hint: '순서 맞추기 · 원인부터 차례로 · 학습용 예시',
      q: '큰손은 왜 엔비디아를 늘렸을까요? 순서대로 눌러보세요.',
      s: ['AI 투자가 늘었어요', 'AI 칩 수요가 늘었어요', '실적 기대가 커졌어요', '보유를 늘렸어요'],
      e: '매니저는 매매 이유를 공개하지 않아요. 그래서 이런 흐름은 뉴스를 바탕으로 한 추정이라는 점을 기억해요.',
    },
  },
  {
    id: 'r3',
    cat: '액티브 ETF',
    kick: 'ETF 읽기 · 예시',
    title: '매니저가 줄이면 나쁜 신호일까요?',
    type: 'O/X',
    quiz: {
      kind: 'ox',
      hint: 'ETF 읽기 · 학습용 예시',
      q: '맞는 말일까요?',
      s: '어제 한 액티브 ETF가 엔비디아를 2% 줄였어요. 엔비디아 전망이 나빠졌다는 뜻이다.',
      a: 'x',
      e: '꼭 그렇진 않아요. 주가가 많이 올라서, 한 종목 비중이 너무 커지지 않게 일부 덜어냈을 수 있어요.',
    },
  },
]

export const labItem = (id: string): LabTopic | LabRec | undefined =>
  [...LAB_TOPICS, ...LAB_RECS].find((x) => x.id === id)
