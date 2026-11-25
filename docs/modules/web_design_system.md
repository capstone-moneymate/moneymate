> 초안입니다. 담당자가 읽고 직접 고쳐서 확정해 주세요.

# 화면 공통 모양 (web/src/styles/design.css · landing.css, components/Mate.tsx, pages/tab1/LessonTop.tsx · Cheer.tsx)

**한 줄 설명**: UI 시안(docs/design/app.html, index.html)의 색·글꼴·버튼·마스코트를 React 화면이 같이 쓰도록 모아 둔 곳.

**입력**
- 색·글꼴 값: `styles/index.css` 의 `@theme` (시안의 `--blue`, `--ink` … 를 `bg-blue`, `text-ink` 같은 Tailwind 이름으로 쓴다). 글꼴 파일은 `web/index.html` 에서 불러온다(Pretendard, Bagel Fat One).
- `Mate`: `mood`(smile·hi·think·happy·wink·wow), `className`(크기).
- `LessonTop`: `progress`(0~100), `onBack`(있으면 뒤로 버튼). 연속 학습 일수는 `useSummary()`(마이페이지와 같은 API)에서 읽는다.
- `Cheer`: 입력 없음.

**하는 일**
- `design.css`: 여러 화면이 같이 쓰는 부품 모양을 `mm-` 로 시작하는 클래스로 둔다 (`mm-btn` 버튼, `mm-chip` 칩, `mm-box` 칸, `mm-opt` 보기, `mm-say` 말풍선, `mm-l-top`·`mm-l-foot` 학습 화면 위·아래, `mm-tabs` 하단 탭 등).
- `landing.css`: 시작 화면(/welcome)에서만 쓰는 모양. 전부 `.landing` 안에서만 먹는다.
- `Mate`: 마스코트 얼굴 SVG 를 표정만 바꿔 그린다.
- `LessonTop`: 카드뉴스·학습·결과 화면 맨 위 줄(닫기 · 뒤로 · 진행 막대 · 연속 학습 일수).
- `Cheer`: 결과 화면에 들어올 때 1.5초 동안 "잘했어요!" 화면을 덮었다가 사라진다.

**출력**: 화면 모양만. 데이터를 만들거나 저장하지 않는다.

**주의할 점**
- 숫자는 여기서 계산하지 않는다. 진행 막대의 %만 화면이 센다(지금 장·단계 ÷ 전체).
- `index.css` 에서 회색(slate) 값도 시안 회색으로 바꿔 두었다. 아직 손보지 않은 화면(탭2 등)이 `text-slate-500` 같은 이름을 쓰기 때문이다.
- 흰 바탕 위 파란 글자는 `text-blue-ink`(진한 파랑)를 쓴다. `text-primary`/`text-blue` 는 글자로 쓰면 흐리다.
- 움직임 줄이기를 켠 기기에서는 시작 화면의 첫 애니메이션과 `Cheer` 를 띄우지 않는다.
- 홈의 "오늘의 트렌드"는 실시간 집계가 아니라 오늘 카드 순위(서버가 준 순서)를 굴려 보여 주는 것이다. 시안의 "실시간 트렌드"에서 이름을 바꿨다.
- 학습 화면의 뒤로 버튼은 이전 단계로 간다. 이미 푼 단계는 푼 상태 그대로 보여 주고 다시 제출하지 않는다. 개념 단계로 돌아가면 튜터를 다시 시작하지 않고 개념 설명만 보여 준다.

**테스트**: 자동 테스트 없음. `pnpm build`·`pnpm lint` 통과, 목 데이터(`VITE_USE_MOCK=true`)로 `pnpm dev` 를 띄워 시작 → 로그인 → 뉴스 홈 → 카드뉴스 → 학습 → 결과 → 마이페이지를 393×852 크기에서 눈으로 확인.
