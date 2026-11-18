# 회원가입·로그인 API (server/auth, web/src/api/auth.ts)

> 초안 (Claude 작성, 2026-11-19). 담당 C가 읽고 고쳐서 확정한다.

**한 줄 설명**: 브라우저 익명 UUID에 아이디·비밀번호를 붙이고, 계정에 붙은 UUID는 그 계정의 로그인 세션에서만 쓰게 하는 가벼운 세션 로그인.

**입력**
- `POST /api/auth/signup` `{userId, loginId, password}`: userId = 지금 브라우저의 익명 UUID. 아이디는 영문 소문자·숫자·_ 4~20자, 비밀번호는 8~64자
- `POST /api/auth/login` `{loginId, password}` / `POST /api/auth/logout` / `GET /api/auth/me`

**하는 일**
1. 가입: `users`의 그 UUID 행에 `login_id`와 `password_hash`(BCrypt)를 채운다(008 migration). 그래서 그동안의 학습 기록이 그대로 이어진다. 가입하면 바로 로그인 상태가 된다.
2. 로그인: 비밀번호가 맞으면 세션 id를 새로 받고(세션 고정 방지) 세션에 `moneymate.userId`를 넣는다. 쿠키는 JSESSIONID 하나(HttpOnly, SameSite=Lax, 7일).
3. `UserGuard`: answers·judgement·mypage·news·stocks API가 받은 userId가 계정 UUID이면, 그 계정의 세션에서 온 요청만 받고 아니면 401. 익명 UUID는 지금처럼 그대로 쓴다.
4. 웹 화면: 처음 열면 시작 화면(`/welcome`: 로그인하기 · 가입하기 · 로그인 없이 둘러보기)이 나온다. 하나를 고르면 `moneymate.entered`를 남겨 다시 나오지 않는다. 마이페이지 맨 위에서도 로그인·가입·로그아웃할 수 있다.
5. 웹: 로그인하면 localStorage userId를 계정 UUID로 바꾼다(기존 API 코드는 그대로). 로그아웃하거나 세션이 끝나면(401) 새 익명 UUID로 시작한다.

**출력**: 가입·로그인·me → `{userId, loginId}`. 오류는 `{message}`: 400 형식 오류, 401 비밀번호 틀림·로그인 필요, 409 아이디 중복·이미 계정인 UUID.

**주의할 점**
- 세션은 서버 메모리에 있다. 서버를 재시작하면 모두 로그아웃된다(웹은 401을 받으면 로그인 화면으로 보낸다).
- 로그인 전에 익명으로 푼 기록은 기존 계정으로 옮기지 않는다(가입할 때만 이어진다).
- 로그인 시도 횟수 제한은 없다. 배포(HTTPS)에서는 `SESSION_COOKIE_SECURE=true`. 웹과 API의 출처가 다르면 axios `withCredentials`와 CORS 설정이 필요하다(지금은 같은 출처).

**테스트 순서**: `server/gradlew.bat test --tests "com.moneymate.auth.*"` → AuthServiceTest(가입·중복·비밀번호), AuthFlowTest(가입 → 세션 → 마이페이지 401/200, 로그아웃).
