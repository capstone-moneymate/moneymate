> **초안 (Claude 작성, 2026-11-16).** 담당자 A가 읽고 고쳐서 확정한다.

# server: GET /api/etf/daily (com.moneymate.etf)

- **한 줄 설명**: 탭2 "액티브 ETF" 화면의 "어제 매니저들이 움직인 종목"을 `holdings_etf`에서 읽어 카드 세 가지(두 ETF가 함께 늘림, 가장 많이 늘림, 가장 많이 줄임)로 나눠 돌려준다. 읽기 전용.
- **입력**: 없음. 기준값은 환경변수 `ETF_DAY_THRESHOLD`(기본 0.05).
- **하는 일** (`EtfService`): ① ETF마다 **자기** 가장 최근 `snapshot_date`의 행만 읽는다 ② `day_chg_pct`(B의 etf_trend.py 값)가 기준 이상이면 늘림, `-기준` 이하면 줄임(경계 포함) ③ 늘림 중 변화율이 큰 (ETF, 종목) 3개 → `topIncrease`, 줄임 중 작은 3개 → `topDecrease` ④ 최신 스냅샷이 있는 **모든** ETF(2개 이상)가 같은 `raw_code`를 늘렸으면 `together`.
- **출력**: `{threshold, etfs[{etfCode, snapshotDate}], together[{ticker, rawCode, stockName, moves[...]}], topIncrease[EtfMove], topDecrease[EtfMove]}`, `EtfMove = {etfCode, ticker, rawCode, stockName, dayChgPct}`. 변화율은 소수.
- **결정 (2026-11-16, A)**: 하루 변화에도 추세와 같은 기준 5%를 쓴다(기준값이 worker `config.ETF_TREND_THRESHOLD`와 server 두 곳에 있으니 하나를 바꾸면 둘 다 바꾼다). TOP은 각 3개. `day_chg_pct`가 NULL인 종목(어제 새로 담음, 또는 그 ETF의 첫 스냅샷)은 보여 주지 않는다.
- **주의할 점**: ETF마다 최신 날짜가 다를 수 있다(한쪽 수집이 빠진 날). 날짜는 `etfs`에 ETF별로 내려가고 화면이 함께 보여 준다. 최신 스냅샷에서 빠진 종목(전량 정리)은 행이 없어 나오지 않는다. `ticker`는 NULL일 수 있어(P16) 두 ETF는 `raw_code`로 맞춘다.
- **테스트**: `cd server; .\gradlew.bat test`. `EtfServiceTest`(가짜 DB 5개: 빈 값, 경계 0.05·-0.05 포함, TOP3 정렬, 함께 늘림은 모든 ETF, ETF 1개면 함께 없음), `EtfApiIntegrationTest`(Testcontainers + `fixtures/etf_daily.sql`, 응답 JSON STRICT 비교. 손계산은 fixture 주석). 공용 컨테이너 준비는 `src/test/java/com/moneymate/TestDatabase.java`.

```bash
curl -s localhost:8080/api/etf/daily
```
