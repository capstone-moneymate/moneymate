# MoneyMate Frontend

moneymate 프론트엔드

## 기술 스택

| 구분            | 사용 기술             |
| --------------- | --------------------- |
| 빌드 / 번들러   | Vite                  |
| UI              | React 19, TypeScript  |
| 스타일          | Tailwind CSS v4       |
| 라우팅          | React Router          |
| 서버 상태       | TanStack Query, Axios |
| 클라이언트 상태 | Zustand               |
| 코드 품질       | ESLint, Prettier      |
| 패키지 매니저   | pnpm                  |

## 시작하기

### 사전 준비

- Node.js 22 이상
- pnpm (`corepack enable` 후 `package.json`의 `packageManager` 버전이 자동으로 사용됩니다)

### 실행

```bash
pnpm install
cp .env.example .env   # 값 채우기
pnpm dev
```

### 스크립트

| 명령어              | 설명                           |
| ------------------- | ------------------------------ |
| `pnpm dev`          | 개발 서버 실행                 |
| `pnpm build`        | 타입 체크 + 프로덕션 빌드      |
| `pnpm preview`      | 빌드 결과물 미리보기           |
| `pnpm lint`         | ESLint 검사                    |
| `pnpm format`       | Prettier로 코드 정리           |
| `pnpm format:check` | Prettier 포맷 검사 (수정 없음) |

## 폴더 구조

```
src/
├── api/         # axios 인스턴스, API 호출 함수
├── components/  # 재사용 UI 컴포넌트
├── hooks/       # 커스텀 훅
├── pages/       # 라우트 단위 페이지
├── store/       # Zustand 전역 상태
├── styles/      # 전역 스타일 (Tailwind 진입점)
├── types/       # 공용 타입 정의
├── App.tsx      # 최상위 Provider (QueryClient, Router)
├── router.tsx   # 라우트 정의
└── main.tsx     # 진입점
```

## 개발 규칙

- import는 `@/` 별칭을 사용합니다. (예: `import { apiClient } from '@/api/client'`)
- 환경변수는 `VITE_` 접두사가 붙어야 브라우저 코드에서 읽을 수 있습니다. 새로 추가하면 `.env.example`과 `src/types/env.d.ts`에도 반영하세요.
- PR을 올리면 CI가 lint와 build를 검사합니다. 올리기 전에 로컬에서 `pnpm lint`와 `pnpm build`를 먼저 확인하세요.
