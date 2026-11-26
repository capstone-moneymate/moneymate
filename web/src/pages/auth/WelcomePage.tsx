import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { markEntered } from '@/lib/entry'

const SIGNUP = '/login?mode=signup&next=/'
const LOGIN = '/login?next=/'

/** 처음 화면(스플래시)이 걷히기까지 걸리는 시간. landing.css 의 애니메이션 길이와 맞춘다 */
const SPLASH_MS = 2680

/**
 * 앱 시작 화면 (/welcome). UI 시안 docs/design/index.html 을 옮긴 소개 화면이다.
 * 처음 열 때만 나온다: 무료로 시작하기(가입) · 로그인 없이 둘러보기 · 로그인.
 * 둘러보기를 고르면 익명 ID 로 쓰고, 나중에 마이페이지에서 가입할 수 있다.
 * 소개 구역의 뉴스 제목·달력·숫자는 서비스를 설명하는 예시이고 화면에도 그렇게 적는다.
 */
export const WelcomePage = () => {
  const navigate = useNavigate()
  const [ready, setReady] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )
  const scrollRef = useRef<HTMLDivElement>(null)
  const heroCta = useRef<HTMLAnchorElement>(null)
  const finalCta = useRef<HTMLAnchorElement>(null)
  const [dock, setDock] = useState(false)

  useEffect(() => {
    if (ready) return
    const timer = window.setTimeout(() => setReady(true), SPLASH_MS)
    return () => window.clearTimeout(timer)
  }, [ready])

  // 아래 붙는 시작 버튼: 맨 위 버튼과 맨 아래 버튼이 둘 다 화면 밖일 때만 보인다
  useEffect(() => {
    const hero = heroCta.current
    const final = finalCta.current
    if (!hero || !final || !('IntersectionObserver' in window)) return
    const seen = { hero: true, final: false }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) seen[e.target === hero ? 'hero' : 'final'] = e.isIntersecting
        setDock(!seen.hero && !seen.final)
      },
      { root: scrollRef.current },
    )
    io.observe(hero)
    io.observe(final)
    return () => io.disconnect()
  }, [])

  const browse = () => {
    markEntered()
    void navigate('/', { replace: true })
  }

  return (
    <div className={`landing ${ready ? 'ready' : ''}`}>
      {!ready && <Splash onSkip={() => setReady(true)} />}

      <div ref={scrollRef} className="l-scroll">
        <header className="hero">
          <div className="bar">
            <span className="mm-wordmark text-[21px]">MONEYMATE</span>
            <Link to={LOGIN}>로그인</Link>
          </div>

          <h1>
            <span style={n(0)}>뉴스 하나로</span>
            <span style={n(1)}>오늘의 투자 공부</span>
            <span style={n(2)}>끝.</span>
          </h1>
          <p className="lede" style={n(3)}>
            매일 그날의 뉴스 한 건을 골라드려요. 카드로 배우고 퀴즈로 확인하면 5분이면 돼요.
          </p>
          <div className="cta" style={n(4)}>
            <Link ref={heroCta} to={SIGNUP} className="mm-btn">
              무료로 시작하기
            </Link>
            <button type="button" onClick={browse} className="mm-btn ghost">
              로그인 없이 둘러보기
            </button>
          </div>
          <Link to={LOGIN} className="sub-link" style={n(5)}>
            이미 계정이 있어요
          </Link>

          <HeroStage />
        </header>

        <main>
          <LoopSection />
          <QuizSection />
          <RecordSection />
        </main>

        <footer className="final">
          <div className="mate2" aria-hidden>
            <svg viewBox="-30 0 260 250">
              <path
                d="M78 178 L72 236 M72 236 h-14M122 178 L128 236 M128 236 h14M22 118 C -8 130, -14 150, -6 168"
                fill="none"
                stroke="#fff"
                strokeWidth="6"
                strokeLinecap="round"
              />
              <path
                className="wave"
                d="M176 112 C 206 96, 216 66, 210 44"
                fill="none"
                stroke="#fff"
                strokeWidth="6"
                strokeLinecap="round"
              />
              <circle cx="100" cy="100" r="86" fill="#FFC94D" stroke="#fff" strokeWidth="6" />
              <g className="mm-eye">
                <ellipse cx="76" cy="86" rx="18" ry="22" fill="#fff" stroke={INK} strokeWidth="5" />
                <ellipse
                  cx="124"
                  cy="86"
                  rx="18"
                  ry="22"
                  fill="#fff"
                  stroke={INK}
                  strokeWidth="5"
                />
                <circle cx="81" cy="90" r="8.5" fill={INK} />
                <circle cx="129" cy="90" r="8.5" fill={INK} />
              </g>
              <path
                d="M82 128q18 18 36 0"
                fill="none"
                stroke={INK}
                strokeWidth="6"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <h2>
            오늘 뉴스부터
            <br />
            같이 볼까요
          </h2>
          <p>가입은 아이디와 비밀번호만 있으면 돼요.</p>
          <Link ref={finalCta} to={SIGNUP} className="mm-btn">
            무료로 시작하기
          </Link>
          <p className="legal">
            머니메이트는 투자 권유가 아닌 학습용 서비스예요.
            <br />이 화면의 뉴스 제목과 숫자는 서비스를 설명하는 예시예요.
          </p>
        </footer>
      </div>

      <div className={`dock ${dock ? 'show' : ''}`}>
        <Link to={SIGNUP} className="mm-btn" tabIndex={dock ? 0 : -1}>
          무료로 시작하기
        </Link>
      </div>
    </div>
  )
}

const INK = '#2B3344'

/** 등장 순서 (landing.css 가 --n × 70ms 만큼 늦춘다) */
const n = (order: number) => ({ '--n': order }) as React.CSSProperties

/** 흩어진 아이콘 한 개의 자리·기울기·늦춤 */
const spot = (x: number, y: number, r: number, d: number, s?: number) =>
  ({
    '--x': `${x}%`,
    '--y': `${y}%`,
    '--r': `${r}deg`,
    '--d': `${d}s`,
    ...(s ? { '--s': `${s}px` } : {}),
  }) as React.CSSProperties

const ICON_PATHS = {
  candle: (
    <>
      <path d="M11 3v5M11 22v7M21 6v6M21 20v6" />
      <rect x="7" y="8" width="8" height="14" rx="2" />
      <rect x="17" y="12" width="8" height="8" rx="2" />
    </>
  ),
  coin: (
    <>
      <circle cx="16" cy="16" r="11" />
      <path d="M10.5 12l2.6 8 2.9-7 2.9 7 2.6-8M10 15.5h12" />
    </>
  ),
  up: <path d="M4 23l8-8 5 5 10-11M20 9h7v7" />,
  card: (
    <>
      <rect x="6" y="4" width="20" height="24" rx="4" />
      <path d="M11 11h10M11 16h10M11 21h6" />
    </>
  ),
}

const SPLASH_ICONS: [keyof typeof ICON_PATHS, React.CSSProperties][] = [
  ['candle', spot(9, 9, -14, 0.05)],
  ['coin', spot(74, 7, 12, 0.22, 34)],
  ['up', spot(84, 26, -10, 0.12)],
  ['card', spot(16, 29, 16, 0.4, 26)],
  ['up', spot(6, 66, 10, 0.28, 32)],
  ['card', spot(82, 68, -18, 0.44, 26)],
  ['coin', spot(26, 77, -8, 0.16, 34)],
  ['candle', spot(62, 80, 14, 0.32)],
  ['up', spot(82, 90, -12, 0.08, 28)],
  ['card', spot(46, 93, 20, 0.38, 26)],
]

/** 처음 들어올 때 한 번: 아이콘이 튀어나오고 워드마크가 올라온 뒤 흰 띠가 화면을 덮으며 걷힌다 */
const Splash = ({ onSkip }: { onSkip: () => void }) => (
  <div className="splash" onClick={onSkip}>
    <div className="splash-icons" aria-hidden>
      {SPLASH_ICONS.map(([name, style], i) => (
        <svg key={i} viewBox="0 0 32 32" style={style}>
          {ICON_PATHS[name]}
        </svg>
      ))}
    </div>
    <div className="splash-core">
      <svg className="splash-face" viewBox="0 0 200 200" aria-hidden>
        <circle cx="100" cy="100" r="88" fill="#FFC94D" stroke="#fff" strokeWidth="6" />
        <ellipse cx="74" cy="92" rx="19" ry="23" fill="#fff" stroke={INK} strokeWidth="5" />
        <ellipse cx="126" cy="92" rx="19" ry="23" fill="#fff" stroke={INK} strokeWidth="5" />
        <circle cx="79" cy="97" r="9" fill={INK} />
        <circle cx="131" cy="97" r="9" fill={INK} />
        <path
          d="M82 134q18 16 36 0"
          fill="none"
          stroke={INK}
          strokeWidth="6"
          strokeLinecap="round"
        />
      </svg>
      <div className="l-display" aria-label="MONEYMATE">
        {[...'MONEYMATE'].map((ch, i) => (
          <span key={i} aria-hidden style={{ '--i': i } as React.CSSProperties}>
            {ch}
          </span>
        ))}
      </div>
      <p className="splash-tag">하루 5분, 뉴스로 배우는 투자</p>
    </div>
    <svg className="ribbons" viewBox="0 0 390 844" preserveAspectRatio="xMidYMid slice" aria-hidden>
      <path
        className="rb-lemon"
        pathLength="1"
        d="M-70 760 C 120 700, 300 640, 250 470 S 60 300, 200 190 S 400 80, 470 -40"
      />
      <path
        className="rb-white"
        pathLength="1"
        d="M-90 900 C 160 820, 60 560, 215 430 S 320 150, 480 -70"
      />
    </svg>
    <button type="button" className="skip">
      건너뛰기
    </button>
  </div>
)

/** 맨 위 그림: 마스코트가 오늘의 뉴스 카드를 들고 있다 */
const HeroStage = () => (
  <div className="stage" aria-hidden>
    <div className="mate">
      <svg viewBox="0 0 200 200">
        <path
          d="M26 110 C -6 120, -10 160, 0 196M174 110 C 206 120, 210 160, 200 196"
          fill="none"
          stroke={INK}
          strokeWidth="6"
          strokeLinecap="round"
        />
        <circle cx="100" cy="100" r="86" fill="#FFC94D" stroke={INK} strokeWidth="6" />
        <g className="mm-eye">
          <ellipse cx="76" cy="80" rx="18" ry="22" fill="#fff" stroke={INK} strokeWidth="5" />
          <ellipse cx="124" cy="80" rx="18" ry="22" fill="#fff" stroke={INK} strokeWidth="5" />
          <circle cx="80" cy="87" r="8.5" fill={INK} />
          <circle cx="128" cy="87" r="8.5" fill={INK} />
        </g>
      </svg>
    </div>
    <div className="newscard">
      <i className="hand l" />
      <i className="hand r" />
      <span className="mm-chip solid">오늘의 주요뉴스</span>
      <h2>연준, 기준금리 동결… 인하는 서두르지 않는다</h2>
      <svg className="spark" viewBox="0 0 300 58" preserveAspectRatio="none">
        <path
          d="M0 44 L30 40 L58 46 L86 30 L112 34 L140 20 L170 26 L198 14 L228 22 L258 9 L300 12"
          fill="none"
          stroke="#F0506A"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <p>카드로 읽고, 퀴즈로 확인하고, 5분</p>
    </div>
  </div>
)

const STEPS = [
  {
    title: '뉴스를 본다',
    body: '오늘 꼭 알아야 할 뉴스 한 건을 카드 몇 장으로 읽어요.',
    mini: (
      <>
        금리는 그대로인데 주가는 왜 움직였을까요?<small>오늘의 뉴스, 1 / 3</small>
      </>
    ),
  },
  {
    title: '개념을 배운다',
    body: '뉴스에 나온 경제 개념을 키워드와 한 줄 정의로 정리해요.',
    mini: (
      <>
        <span className="pill on">기준금리</span>
        <small style={{ marginTop: 8 }}>중앙은행이 정하는, 모든 금리의 기준이 되는 금리</small>
      </>
    ),
  },
  {
    title: '퀴즈로 확인한다',
    body: '골라 맞히기, 원인부터 결과까지 순서 맞추기, 차트 읽기까지.',
    mini: (
      <>
        <div className="bars">
          {[40, 62, 48, 80].map((h) => (
            <b key={h} style={{ height: `${h}%` }} />
          ))}
          <b style={{ height: '100%', background: 'var(--color-up)' }} />
        </div>
        <small>차트에서 무엇이 보이나요?</small>
      </>
    ),
  },
  {
    title: '내 판단을 적는다',
    body: '나라면 어떻게 볼지 고르고, 그 이유를 직접 써봐요.',
    mini: (
      <>
        <div className="row">
          <span className="pill">추가매수</span>
          <span className="pill on">관망</span>
          <span className="pill">차익실현</span>
        </div>
        <small style={{ marginTop: 8 }}>근거를 쓰면 피드백과 점수를 받아요</small>
      </>
    ),
  },
  {
    title: '기록이 쌓인다',
    body: '배운 날은 달력에, 배운 개념은 인과 지도에 남아요.',
    mini: (
      <>
        6일 연속 학습 중<small>배운 카드뉴스 13개</small>
      </>
    ),
  },
]

/** 다섯 단계 소개: 옆으로 넘기는 카드 + 아래 점 */
const LoopSection = () => {
  const loop = useRef<HTMLDivElement>(null)
  const [current, setCurrent] = useState(0)

  const onScroll = () => {
    const el = loop.current
    if (!el) return
    const mid = el.scrollLeft + el.clientWidth / 2
    let best = 0
    let bestGap = Infinity
    Array.from(el.children).forEach((child, i) => {
      const c = child as HTMLElement
      const gap = Math.abs(c.offsetLeft - el.offsetLeft + c.offsetWidth / 2 - mid)
      if (gap < bestGap) {
        bestGap = gap
        best = i
      }
    })
    setCurrent(best)
  }

  return (
    <section className="sec" aria-labelledby="loop-t">
      <h2 className="t" id="loop-t">
        읽고, 배우고,
        <br />내 생각까지 적어요
      </h2>
      <p className="d">뉴스 하나가 다섯 단계를 거쳐 내 지식이 돼요. 옆으로 넘겨보세요.</p>

      <div className="loop" ref={loop} onScroll={onScroll}>
        {STEPS.map((s, i) => (
          <article className="step" key={s.title}>
            <span className="no">{i + 1}</span>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
            <div className="mini">{s.mini}</div>
          </article>
        ))}
      </div>
      <div className="mm-dots" aria-hidden>
        {STEPS.map((s, i) => (
          <i key={s.title} className={i === current ? 'on' : ''} />
        ))}
      </div>
    </section>
  )
}

const QUIZ_OPTIONS = ['바로 크게 오른다', '당분간 크게 안 움직인다', '바로 크게 내린다']
const QUIZ_ANSWER = 1

/** 맛보기 퀴즈 한 문제. 이 화면 안에서만 채점하고 기록하지 않는다 */
const QuizSection = () => {
  const [picked, setPicked] = useState<number | null>(null)
  const done = picked !== null

  return (
    <section className="sec" aria-labelledby="quiz-t">
      <h2 className="t" id="quiz-t">
        한 문제만
        <br />
        먼저 풀어볼까요
      </h2>
      <p className="d">앱에서는 이런 퀴즈가 매일 뉴스와 함께 나와요.</p>

      <div className="quiz">
        <p className="q">금리를 “동결”하면, 대출·예금 금리는 어떻게 될까요?</p>
        <div className="mm-opts">
          {QUIZ_OPTIONS.map((option, i) => (
            <button
              key={option}
              type="button"
              disabled={done}
              onClick={() => setPicked(i)}
              className={`mm-opt ${
                done ? (i === QUIZ_ANSWER ? 'right' : i === picked ? 'wrong' : 'dim') : ''
              }`}
            >
              <span className="k">{'ABC'[i]}</span>
              {option}
            </button>
          ))}
        </div>
        <div className={`explain ${done ? 'open' : ''}`} aria-live="polite">
          <div>
            <div className="box">
              <strong>{picked === QUIZ_ANSWER ? '정답이에요' : '아쉬워요, 정답은 B예요'}</strong>
              동결은 금리를 그대로 두는 거라, 대출·예금 금리도 당분간 크게 변하지 않아요.
            </div>
            <button
              type="button"
              className="retry"
              tabIndex={done ? 0 : -1}
              onClick={() => setPicked(null)}
            >
              다시 풀기
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

/** 예시 달력: 2026년 11월(일요일에 시작), 파란 날이 배운 날 */
const DEMO_DONE = [3, 4, 5, 9, 10, 11, 12, 16, 17, 18, 19, 20]
const DEMO_TODAY = 21

/** 기록 소개: 달력 / 인과 지도 예시를 번갈아 본다 */
const RecordSection = () => {
  const [view, setView] = useState<'cal' | 'map'>('cal')

  return (
    <section className="sec" aria-labelledby="rec-t">
      <h2 className="t" id="rec-t">
        배운 건
        <br />
        사라지지 않아요
      </h2>
      <p className="d">마이페이지에서 얼마나 꾸준했는지, 개념이 어떻게 이어지는지 볼 수 있어요.</p>

      <div className="me">
        <div className="stat">
          <b>6일</b>
          <span>연속 학습</span>
        </div>
        <div className="stat">
          <b>13개</b>
          <span>배운 카드뉴스</span>
        </div>
      </div>

      <div className="seg" role="tablist" aria-label="기록 보기 전환">
        <button
          type="button"
          role="tab"
          aria-selected={view === 'cal'}
          onClick={() => setView('cal')}
        >
          달력
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === 'map'}
          onClick={() => setView('map')}
        >
          인과 지도
        </button>
      </div>

      {view === 'cal' ? (
        <div className="panel" role="tabpanel">
          <div className="cal-h">
            2026년 11월 <small>파란 날이 배운 날</small>
          </div>
          <div className="mm-cal">
            {[...'일월화수목금토'].map((d) => (
              <span key={d}>{d}</span>
            ))}
            {Array.from({ length: 30 }, (_, i) => i + 1).map((d) => (
              <em
                key={d}
                className={`d not-italic ${
                  d === DEMO_TODAY ? 'today' : DEMO_DONE.includes(d) ? 'bg-blue text-white' : ''
                }`}
              >
                {d}
              </em>
            ))}
          </div>
        </div>
      ) : (
        <div className="panel" role="tabpanel">
          <span className="mm-chip solid mb-3.5 h-[30px] text-[13.5px]">테마: 금리</span>
          <ol className="chain">
            <li>
              <b>의장 “인하를 서두르지 않겠다”</b>
            </li>
            <li>
              <b>금리 인하 기대가 줄어든다</b>
              <span className="tag down">누르는 힘</span>
            </li>
            <li>
              <b>금리가 오래 높게 유지된다</b>
              <span className="tag down">누르는 힘</span> <span className="tag re">복습 필요</span>
            </li>
            <li>
              <b>실적이 좋으면 버티는 종목도 있다</b>
              <span className="tag up">올리는 힘</span>
            </li>
            <li>
              <b>결과: 성장주에 부담</b>
            </li>
          </ol>
        </div>
      )}
      <p className="l-note">화면 속 날짜와 수치는 예시예요.</p>
    </section>
  )
}
