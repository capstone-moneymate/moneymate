import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router'
import { useSummary } from '@/api/mypage'
import { Mate } from '@/components/Mate'
import { LAB_RECS, LAB_TOPICS, labItem } from '@/pages/lab/labData'
import type { LabQuiz, LabRec, LabTopic } from '@/pages/lab/labData'
import { labStatus, loadLab, saveLab } from '@/pages/lab/labProgress'
import type { LabProgress } from '@/pages/lab/labProgress'
import { Cheer } from '@/pages/tab1/Cheer'
import { LessonTop } from '@/pages/tab1/LessonTop'
import { VerdictIcon } from '@/pages/tab1/steps/AnswerFeedback'

/** 한 단계: 개념 설명(c) 또는 문제(q) */
interface LabStep {
  t: 'c' | 'q'
  it: LabTopic | LabRec
}

/** 문제 하나를 푸는 동안의 상태 */
interface QuizState {
  /** 객관식·빈칸: 보기 번호, O/X: 'o' | 'x' */
  sel: number | 'o' | 'x' | null
  /** 순서 맞추기: 누른 순서 */
  pick: number[]
  /** 짝 맞추기: 왼쪽 i 번에 넣은 오른쪽 번호 */
  pairs: (number | null)[]
  /** 순서·짝 맞추기에서 섞어 보여 주는 순서 */
  rows: number[]
  done: boolean
  /** 다 고르지 않고 [잘 모르겠어요]로 답을 봤다 */
  skip: boolean
}

const shuffled = (n: number): number[] => {
  const base = Array.from({ length: n }, (_, i) => i)
  if (n < 2) return base
  let out = base
  // 정답 순서 그대로 나오지 않을 때까지 섞는다
  while (out.every((v, i) => v === i)) {
    out = [...base]
    for (let i = out.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[out[i], out[j]] = [out[j], out[i]]
    }
  }
  return out
}

const initState = (q: LabQuiz): QuizState => {
  const n = q.kind === 'order' ? q.s.length : q.kind === 'match' ? q.l.length : 0
  return {
    sel: null,
    pick: [],
    pairs: q.kind === 'match' ? Array<number | null>(n).fill(null) : [],
    rows: shuffled(n),
    done: false,
    skip: false,
  }
}

const isReady = (q: LabQuiz, st: QuizState) =>
  q.kind === 'order'
    ? st.pick.length === q.s.length
    : q.kind === 'match'
      ? !st.pairs.includes(null)
      : st.sel !== null

/** 채점은 화면이 한다 (정답이 labData 에 있다) */
const isRight = (q: LabQuiz, st: QuizState) => {
  if (st.skip) return false
  if (q.kind === 'order') return st.pick.length === q.s.length && st.pick.every((v, i) => v === i)
  if (q.kind === 'match') return st.pairs.every((v, i) => v === i)
  return st.sel === q.a
}

const answerText = (q: LabQuiz) =>
  q.kind === 'mcq'
    ? 'ABC'[q.a]
    : q.kind === 'ox'
      ? q.a === 'o'
        ? '“맞아요”'
        : '“아니에요”'
      : q.kind === 'blank'
        ? `“${q.o[q.a]}”`
        : ''

/** 기초 자료는 개념 → 문제, 큰손 기록은 고른 문제부터 남은 문제까지 이어서 푼다 */
const buildSteps = (kind: string, id: string, progress: LabProgress): LabStep[] => {
  if (kind === 'topic') {
    const it = LAB_TOPICS.find((x) => x.id === id)
    return it
      ? [
          { t: 'c', it },
          { t: 'q', it },
        ]
      : []
  }
  const from = LAB_RECS.findIndex((x) => x.id === id)
  if (from < 0) return []
  return LAB_RECS.slice(from)
    .filter((r, j) => j === 0 || labStatus(progress, r.id) !== 'done')
    .map((it) => ({ t: 'q' as const, it }))
}

/**
 * 분석 자료 퀴즈 화면 (/lab/topic/:id, /lab/rec/:id). UI 시안 app.html 의 자료 퀴즈를 옮겼다.
 * 문제 종류 다섯 가지: 객관식 · O/X · 빈칸 채우기 · 짝 맞추기 · 순서 맞추기.
 * 아래 버튼은 [잘 모르겠어요] [확인]. 잘 모르겠어요는 고르지 않아도 누를 수 있고 정답을 보여 준다.
 * 모든 자료를 다 풀면 마지막에 완료 화면이 나온다.
 */
export const LabQuizPage = () => {
  const { kind = '', id = '' } = useParams()
  // key: 다른 자료로 바뀌면 처음부터
  return <LabSession key={`${kind}:${id}`} kind={kind} id={id} />
}

const LabSession = ({ kind, id }: { kind: string; id: string }) => {
  const navigate = useNavigate()
  const [progress, setProgress] = useState(loadLab)
  const [steps] = useState(() => buildSteps(kind, id, progress))
  const [states, setStates] = useState(() => steps.map((s) => initState(s.it.quiz)))
  const [index, setIndex] = useState(0)
  const [finished, setFinished] = useState(false)
  const step = steps[index]

  // 처음 연 자료는 "이어 풀기"로 저장해 둔다 (분석 자료 홈이 다시 읽는다)
  useEffect(() => {
    if (step && labStatus(loadLab(), step.it.id) === 'new') {
      saveLab(step.it.id, { st: 'started' })
    }
  }, [step])

  if (!step || !labItem(id)) return <Navigate to="/lab" replace />
  if (finished) return <LabResult progress={progress} />

  const q = step.it.quiz
  const st = states[index]
  const update = (patch: Partial<QuizState>) =>
    setStates(states.map((s, i) => (i === index ? { ...s, ...patch } : s)))

  const check = (unsure: boolean) => {
    const next = { ...st, done: true, skip: unsure && !isReady(q, st) }
    update(next)
    setProgress(saveLab(step.it.id, { st: 'done', ok: isRight(q, next) }))
  }

  const goOn = () => {
    if (index < steps.length - 1) setIndex(index + 1)
    else if ([...LAB_TOPICS, ...LAB_RECS].every((x) => labStatus(progress, x.id) === 'done'))
      setFinished(true)
    else void navigate('/lab')
  }

  const asked = step.t === 'q'
  const ok = asked && st.done ? isRight(q, st) : null
  const percent = Math.round(((index + 1 + (asked && st.done ? 1 : 0)) / (steps.length + 1)) * 100)
  const tone = ok === null ? '' : st.skip ? 'hm' : ok ? 'ok' : 'no'
  const answer = answerText(q)
  const tail = answer ? `, 정답은 ${answer}예요` : ''

  return (
    <div className="flex h-full flex-col">
      <LabTop percent={percent} onBack={index > 0 ? () => setIndex(index - 1) : undefined} />

      <div className="min-h-0 flex-1 overflow-y-auto">
        {/* key: 단계가 바뀌면 내용이 옆에서 다시 들어온다 */}
        <div className="mm-l-body" key={index}>
          {step.t === 'c' ? (
            <ConceptBody topic={step.it as LabTopic} />
          ) : (
            <>
              <div className="mm-say">
                <Mate mood={ok ? 'happy' : 'think'} />
                <div className="mm-bub">
                  <small>{q.hint}</small>
                  <p>{q.q}</p>
                </div>
              </div>
              <QuizBody q={q} st={st} update={update} />
            </>
          )}
        </div>
      </div>

      {step.t === 'c' ? (
        <div className="mm-l-foot">
          <button type="button" onClick={() => setIndex(index + 1)} className="mm-btn">
            알겠어요
          </button>
        </div>
      ) : !st.done ? (
        <div className="mm-l-foot">
          <div className="mm-two">
            <button type="button" onClick={() => check(true)} className="mm-btn ghost">
              잘 모르겠어요
            </button>
            <button
              type="button"
              onClick={() => check(false)}
              disabled={!isReady(q, st)}
              className="mm-btn"
            >
              확인
            </button>
          </div>
        </div>
      ) : (
        <div className={`mm-l-foot ${tone} max-h-[62%] overflow-y-auto`}>
          <div role="status">
            <p className="mm-verdict">
              {st.skip ? <HmmIcon /> : <VerdictIcon ok={ok === true} />}
              {st.skip
                ? `괜찮아요${tail || ', 정답은 이래요'}`
                : ok
                  ? '정답이에요!'
                  : `아쉬워요${tail || (q.kind === 'order' ? ', 순서가 달라요' : ', 짝이 달라요')}`}
            </p>
            <p className="mm-why">{q.e}</p>
          </div>
          <button type="button" onClick={goOn} className="mm-btn">
            계속하기
          </button>
        </div>
      )}
    </div>
  )
}

/** 위쪽 줄 (학습 화면과 같다): 닫기(분석 자료 홈으로) · 뒤로 · 진행 막대 · 연속 학습 일수 */
const LabTop = ({ percent, onBack }: { percent: number; onBack?: () => void }) => (
  <LessonTop
    progress={percent}
    onBack={onBack}
    backLabel="이전 단계로 돌아가기"
    closeTo="/lab"
    closeLabel="그만하고 분석 자료 홈으로"
  />
)

const ConceptBody = ({ topic }: { topic: LabTopic }) => (
  <>
    <div className="mm-say">
      <Mate mood="hi" />
      <div className="mm-bub">
        <small>분석 자료 기초 · {topic.name}</small>
        <p>이 자료, 들어본 적 있나요?</p>
      </div>
    </div>
    <article className="mm-box mm-concept">
      <span className="mm-chip gray">한 줄로 보면</span>
      <h2 className="kw">{topic.kw ?? topic.name}</h2>
      <p className="def">{topic.d}</p>
      <ul className="mm-pts">
        {topic.p.map((x) => (
          <li key={x}>{x}</li>
        ))}
      </ul>
    </article>
  </>
)

interface QuizBodyProps {
  q: LabQuiz
  st: QuizState
  update: (patch: Partial<QuizState>) => void
}

/** 문제 종류별 보기. 채점 뒤(st.done)에는 정답은 파랑, 내가 고른 오답은 빨강 */
const QuizBody = ({ q, st, update }: QuizBodyProps) => {
  const show = st.done
  const mark = (right: boolean, mine: boolean) =>
    show ? (right ? 'right' : mine ? 'wrong' : '') : ''

  if (q.kind === 'mcq') {
    return (
      <>
        {q.ctx && (
          <p className="mm-ctx">
            <small>{q.ctx[0]}</small>
            {q.ctx[1]}
          </p>
        )}
        <div className="mm-opts">
          {q.o.map((option, i) => (
            <button
              key={option}
              type="button"
              disabled={show}
              onClick={() => update({ sel: i })}
              aria-pressed={!show && st.sel === i}
              className={`mm-opt ${mark(i === q.a, i === st.sel)}`}
            >
              <span className="k">{'ABC'[i]}</span>
              {option}
            </button>
          ))}
        </div>
      </>
    )
  }

  if (q.kind === 'ox') {
    return (
      <>
        <p className="mm-box mm-stmt">{q.s}</p>
        <div className="mm-oxpair">
          {(['o', 'x'] as const).map((v) => (
            <button
              key={v}
              type="button"
              disabled={show}
              onClick={() => update({ sel: v })}
              aria-pressed={!show && st.sel === v}
              className={`mm-box ${mark(v === q.a, v === st.sel)}`}
            >
              <svg viewBox="0 0 42 42" aria-hidden>
                {v === 'o' ? <circle cx="21" cy="21" r="13" /> : <path d="M9 9l24 24M33 9L9 33" />}
              </svg>
              {v === 'o' ? '맞아요' : '아니에요'}
            </button>
          ))}
        </div>
      </>
    )
  }

  if (q.kind === 'blank') {
    const sel = typeof st.sel === 'number' ? st.sel : null
    // 고르지 않고 답을 봤으면 빈칸에 정답을 채워 보여 준다
    const shown = show && (st.skip || sel === null) ? q.a : sel
    const bad = show && !st.skip && sel !== q.a
    return (
      <>
        <p className="mm-box mm-stmt">
          {q.pre}
          <span className={`mm-blank ${shown !== null ? 'fill' : ''} ${bad ? 'bad' : ''}`}>
            {shown !== null ? q.o[shown] : ''}
          </span>
          {q.post}
        </p>
        <div className="mm-chips">
          {q.o.map((option, i) => (
            <button
              key={option}
              type="button"
              disabled={show || sel === i}
              onClick={() => update({ sel: i })}
            >
              {option}
            </button>
          ))}
        </div>
      </>
    )
  }

  if (q.kind === 'match') {
    const active = st.pairs.indexOf(null)
    return (
      <>
        <div className="mm-match">
          {q.l.map((label, i) => {
            const v = show && st.skip ? i : st.pairs[i]
            const cls = show ? (st.skip || v === i ? 'ok' : 'bad') : i === active ? 'act' : ''
            return (
              <div key={label} className={`row ${cls}`}>
                <span className="ml">{label}</span>
                <button
                  type="button"
                  disabled={show || v === null}
                  onClick={() => update({ pairs: st.pairs.map((p, j) => (j === i ? null : p)) })}
                  aria-label={
                    v !== null
                      ? `${label}, ${q.r[v]} 연결됨. 누르면 빼요`
                      : `${label}, 아직 비어 있어요`
                  }
                  className={`mr ${v !== null ? 'fill' : ''}`}
                >
                  {v !== null ? q.r[v] : '아래에서 골라요'}
                </button>
              </div>
            )
          })}
        </div>
        {!show && (
          <div className="mm-chips">
            {st.rows
              .filter((v) => !st.pairs.includes(v))
              .map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => update({ pairs: st.pairs.map((p, j) => (j === active ? v : p)) })}
                >
                  {q.r[v]}
                </button>
              ))}
          </div>
        )}
      </>
    )
  }

  return (
    <div className="mm-opts">
      {st.rows.map((v) => {
        const at = st.pick.indexOf(v)
        const cls = show
          ? st.skip
            ? 'shown'
            : at === v
              ? 'right'
              : 'wrong'
          : at < 0
            ? 'k-empty'
            : ''
        return (
          <button
            key={v}
            type="button"
            disabled={show}
            onClick={() =>
              update({ pick: at > -1 ? st.pick.filter((x) => x !== v) : [...st.pick, v] })
            }
            aria-pressed={!show && at > -1}
            className={`mm-opt ${cls}`}
          >
            <span className="k">{show && st.skip ? v + 1 : at > -1 ? at + 1 : '0'}</span>
            {q.s[v]}
          </button>
        )
      })}
    </div>
  )
}

/** 모든 자료를 다 풀었을 때의 완료 화면 */
const LabResult = ({ progress }: { progress: LabProgress }) => {
  const streak = useSummary().data?.streakDays
  const all = [...LAB_TOPICS, ...LAB_RECS]
  const right = all.filter((x) => progress[x.id]?.ok).length

  return (
    <div className="relative flex h-full flex-col overflow-hidden">
      <Cheer />
      <LabTop percent={100} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mm-l-body">
          <div className="mm-done-top">
            <Mate mood="happy" />
            <h2>자료 퀴즈 완료!</h2>
            <p>이제 큰손의 기록을 읽을 수 있어요.</p>
          </div>
          <dl className="mm-scores">
            <div className="mm-score main">
              <dt>배운 자료</dt>
              <dd>
                {LAB_TOPICS.length}
                <small>개</small>
              </dd>
            </div>
            <div className="mm-score">
              <dt>맞힌 문제</dt>
              <dd>
                {right}
                <small> / {all.length}</small>
              </dd>
            </div>
            <div className="mm-score">
              <dt>연속 학습</dt>
              <dd>
                {streak ?? '-'}
                <small>일</small>
              </dd>
            </div>
          </dl>
          <div className="mm-h-sec">
            <h3>오늘 배운 자료</h3>
          </div>
          <ul className="mm-did">
            {[
              '13F 보고서 · 액티브 ETF',
              '내부자 거래 공시 · 실적 발표',
              '사업보고서 · 애널리스트 리포트',
              `큰손 기록으로 풀어보기 ${LAB_RECS.length}문제`,
            ].map((line) => (
              <li key={line}>
                <VerdictIcon ok />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="mm-l-foot">
        <Link to="/lab" className="mm-btn">
          분석 자료 홈으로
        </Link>
      </div>
    </div>
  )
}

/** 동그라미 안의 물음표 (잘 모르겠어요로 답을 봤을 때) */
const HmmIcon = () => (
  <svg viewBox="0 0 30 30" aria-hidden>
    <circle cx="15" cy="15" r="15" fill="currentColor" />
    <path
      d="M11.5 12a3.5 3.5 0 1 1 5.3 3c-1.1.7-1.8 1.4-1.8 2.6"
      fill="none"
      stroke="#fff"
      strokeWidth="2.8"
      strokeLinecap="round"
    />
    <circle cx="15" cy="21.8" r="1.7" fill="#fff" />
  </svg>
)
