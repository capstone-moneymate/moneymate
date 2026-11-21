> **초안 (Claude 작성, 2026-11-21).** 담당자 C가 읽고 고쳐서 확정한다.

# web: 탭3 학습 달력 (pages/tab3/StudyCalendar.tsx, MyPage.tsx)

- **한 줄 설명**: 마이페이지에서 문제를 푼 날을 달력에 남색 동그라미로 보여 주고, 날짜를 누르면 그날 푼 카드뉴스를 다시 보거나 퀴즈를 다시 풀게 한다.
- **입력**: `GET /api/mypage/calendar?userId=` → `{days:[{date, cards:[{cardId,title,cardDate,stepCount,answered,graded,correct}]}]}` (최근 400일, 최근 날짜 먼저). 연속 학습 일수는 `/api/mypage/summary`의 `streakDays`.
- **하는 일**: ① 첫 학습 달 ~ 이번 달(KST)을 가로로 넘기는 달력으로 그리고, 처음엔 이번 달을 보여 준다 ② 푼 날은 남색 동그라미, 오늘은 진한 테두리, 미래 날짜는 흐린 글자 ③ 동그라미를 누르면 아래에 그날 카드 목록: 제목, "문제 N개 중 M개 맞힘", 지난 뉴스를 풀었으면 카드 날짜 표시, 버튼 "카드뉴스 보기"(`/news/:id`)·"퀴즈 다시 풀기"(`/news/:id/learn`) ④ 위쪽 "카드뉴스 N장"은 달력에 나온 서로 다른 카드 수.
- **출력**: 화면만. 다시 푼 답안은 탭1 학습 화면이 평소처럼 `POST /api/answers`로 저장한다.
- **주의할 점**: 날짜는 서버처럼 KST로 자른다. 숫자는 서버가 센 값을 그대로 보여 준다(같은 날 같은 문제를 다시 냈으면 그날 마지막 답안 기준). 다시 풀기는 기록을 덮어쓰지 않고 새 답안이 쌓인다 — 다시 푼 날도 달력에 표시된다. 인과 지도 탭은 기존 `CausalMapView`를 그대로 넣었다(`/mypage/map` 화면도 남아 있음). 탭은 `?view=map`으로 주소에 남는다.
- **테스트**: `MypageServiceTest` 2개(날짜 묶기·순서 유지, 기록 없음 → 빈 배열). SQL은 2026-11-21 로컬 PostgreSQL에서 트랜잭션 안에 시험 답안 4개(KST 자정 경계, 같은 날 다시 낸 답)를 넣고 돌려 손계산(11/19 카드1 답 2·채점 1·정답 1, 11/18 카드2 1·1·1)과 같음을 확인 후 ROLLBACK. 화면은 `VITE_USE_MOCK=true`(api/mocks/calendar.ts)로 390px에서 확인.
