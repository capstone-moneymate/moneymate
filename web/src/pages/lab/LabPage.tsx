import { useState } from 'react'
import { Link } from 'react-router'
import { Mate } from '@/components/Mate'
import { LAB_CATS, LAB_RECS, LAB_TOPICS } from '@/pages/lab/labData'
import { labStatus, loadLab } from '@/pages/lab/labProgress'

/**
 * 분석 자료 탭 홈 (UI 시안 app.html 의 "분석 자료").
 * 위: 제목 · 검색 · 자료 종류 칩. 가운데: 오늘의 기초 퀴즈 배너(아직 안 푼 첫 자료).
 * 아래: 분석 자료 기초(가로로 넘기는 카드 6개) · 큰손 기록으로 풀어보기(학습용 예시 3문제).
 * 내용은 화면에 들어 있는 고정 내용이고(labData), 진행 기록은 이 기기에만 남는다(labProgress).
 */
export const LabPage = () => {
  const [progress] = useState(loadLab)
  const [cat, setCat] = useState('전체')
  const [searching, setSearching] = useState(false)
  const [query, setQuery] = useState('')

  const q = query.trim().toLowerCase()
  const show = (itemCat: string, text: string) =>
    (cat === '전체' || itemCat === cat) && (!q || text.toLowerCase().includes(q))
  const topics = LAB_TOPICS.filter((x) => show(x.cat, `${x.name} ${x.badge} ${x.sub}`))
  const recs = LAB_RECS.filter((x) => show(x.cat, `${x.title} ${x.kick}`))
  const doneCount = LAB_TOPICS.filter((x) => labStatus(progress, x.id) === 'done').length
  const next = LAB_TOPICS.find((x) => labStatus(progress, x.id) !== 'done')

  return (
    <div className="pb-4">
      <header className="px-5 pt-[calc(12px+env(safe-area-inset-top))]">
        <div className="flex items-center gap-2">
          <h1 className="flex-1 text-[22px] font-extrabold tracking-[-0.02em]">분석 자료</h1>
          <button
            type="button"
            onClick={() => {
              setSearching(!searching)
              setQuery('')
            }}
            aria-label="분석 자료 검색"
            aria-expanded={searching}
            className={`mm-round size-[42px] basis-[42px] ${searching ? 'border-blue bg-blue-soft' : ''}`}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              aria-hidden
            >
              <circle cx="11" cy="11" r="6.5" />
              <path d="M16 16l4.5 4.5" />
            </svg>
          </button>
        </div>
        {searching && (
          <label className="mt-2.5 block">
            <span className="sr-only">분석 자료 검색</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
              autoComplete="off"
              placeholder="자료 이름을 검색하세요"
              className="border-blue h-[46px] w-full rounded-[14px] border-2 px-3.5 text-base font-semibold outline-none"
            />
          </label>
        )}
        <div className="mm-cats" role="tablist" aria-label="자료 종류">
          {LAB_CATS.map((c) => (
            <button
              key={c}
              type="button"
              role="tab"
              aria-selected={c === cat}
              onClick={() => setCat(c)}
            >
              {c}
            </button>
          ))}
        </div>
      </header>

      <div className="px-5 pt-3.5">
        <section className="mm-banner">
          <Mate mood={next ? 'think' : 'happy'} />
          <div>
            <small>
              {next ? '오늘의 기초 퀴즈 · 3분' : `기초 자료 ${LAB_TOPICS.length}개 완료`}
            </small>
            <strong>{next ? `${next.name}란 무엇일까요?` : '처음부터 다시 풀어볼까요?'}</strong>
            <Link to={`/lab/topic/${(next ?? LAB_TOPICS[0]).id}`} className="mm-btn butter">
              {next ? '바로 풀기' : '다시 풀기'}
            </Link>
          </div>
        </section>

        <div className="mm-h-sec mt-4 mb-2">
          <h2>분석 자료 기초</h2>
          <small>
            {doneCount} / {LAB_TOPICS.length} 완료
          </small>
        </div>
      </div>
      {topics.length > 0 ? (
        <div className="mm-slider">
          {topics.map((x) => {
            const st = labStatus(progress, x.id)
            return (
              <Link key={x.id} to={`/lab/topic/${x.id}`} className="mm-box mm-tcard">
                <span className="bdg" style={{ background: x.color }}>
                  {x.badge}
                </span>
                <b>{x.name}</b>
                <span className="sub">{x.sub}</span>
                <span
                  className={`mm-chip ${st === 'done' ? 'gray' : st === 'started' ? 'solid' : 'line text-sub'}`}
                >
                  {st === 'done' ? '완료' : st === 'started' ? '이어 풀기' : '시작 전'}
                </span>
              </Link>
            )
          })}
        </div>
      ) : (
        <p className="mm-none">맞는 기초 자료가 없어요.</p>
      )}

      {recs.length > 0 && (
        <>
          <div className="mm-h-sec mt-4 mb-2 px-5">
            <h2>큰손 기록으로 풀어보기</h2>
            <small>학습용 예시</small>
          </div>
          <div className="mm-slider">
            {recs.map((x) => {
              const done = labStatus(progress, x.id) === 'done'
              return (
                <Link key={x.id} to={`/lab/rec/${x.id}`} className="mm-box mm-rcard">
                  <small>{x.kick}</small>
                  <b>{x.title}</b>
                  <span className={`mm-chip ${done ? 'gray' : 'butter'}`}>
                    {done ? '완료' : x.type}
                  </span>
                </Link>
              )
            })}
          </div>
          <p className="text-faint mt-2 px-5 text-center text-[11.5px] font-semibold">
            문제 속 종목·인물·숫자는 읽는 법을 익히기 위한 예시예요.
          </p>
        </>
      )}
    </div>
  )
}
