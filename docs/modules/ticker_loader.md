> **초안 (Claude 작성, 2026-11-16).** 담당자 A가 읽고 고쳐서 확정한다. 아래 매핑 표도 **초안이고 팀 검토가 필요하다.**

# worker/concepts/ticker_loader.py + db/seeds/concept_tickers.csv

- **한 줄 설명**: 개념↔티커 매핑 CSV를 검사한 뒤 `concept_tickers` 테이블(005)에 CSV와 똑같이 맞춰 넣는다. 탭 2의 "내 지도에 있어요"에 쓴다.
- **입력**: `db/seeds/concept_tickers.csv`(머리줄 `concept_id,ticker,market,reason,source,status`), B의 `db/seeds/concepts.csv`(개념 id 확인용), `--save`.
- **하는 일**: ① 줄마다 검사한다: 개념 id가 사전에 있는지, `market` US/KR, 티커 형식(미국 `^[A-Z]+(-[A-Z]+)?$`, 한국 6자리 `^[0-9A-Z]{6}$`, 005의 CHECK와 같은 식), `reason`이 비었는지, `source`가 https 링크인지, `status` draft/approved. (개념, 티커) 중복도 검사한다. 문제는 줄 번호와 함께 전부 모아 한 번에 알려 준다 ② DB `concepts`에 개념이 없으면 FK 오류 대신 "먼저 `python -m concepts.loader --save`"라고 알려 준다 ③ upsert한다. 값이 같은 행은 건드리지 않아 `updated_at`이 그대로다 ④ CSV에서 지운 행은 DB에서도 지운다.
- **출력**: 새로 넣은 행, 바꾼 행, 지운 행. `--save`가 없으면 되돌리고 출력만 한다.
- **주의할 점**: 개념 id는 B의 사전 id만 쓴다. 탭 2가 `user_concepts.concept_id`와 그대로 비교하기 때문이다. 새 개념이 필요하면 B에게 먼저 말한다. 연결은 SEC 공시(10-K·20-F) 사업 설명으로 확인한 것만 넣는다. 검토 전이라 서버 쿼리는 `status`를 거르지 않는다(draft도 나온다).
- **테스트**: `python -m pytest tests/test_ticker_loader.py -q` 23개. 형식·사전 id·빈 값·중복·머리줄 거부, 실제 초안 통과, 로컬 DB에서 되돌리는 트랜잭션으로 재적재 시 변화 0·고친 행만 바뀜·뺀 행 지움, 사전 미적재 안내, DB CHECK 거부. DB 테스트는 로컬 DB가 없거나 005가 없으면 건너뛴다. 2026-11-16 로컬 DB에서 `--save`를 두 번 실행했다. 첫 번째는 새로 넣음 18, 두 번째는 0·0·0.

## 매핑 초안 (18줄, 전부 draft)

근거는 각 회사의 최신 연간 보고서다. 2026-11-16에 edgartools로 받은 본문에서 문구를 찾아 확인했다.

| 개념 | 종목 | 공시 문구 (요약) |
|---|---|---|
| ai_investment | GOOGL | "invest in capital expenditures as we scale our technical infrastructure, in particular for AI" (10-K 2026-02) |
| ai_investment | MSFT | "investments we are making in cloud and AI infrastructure… require substantial and increasing capital expenditures" (10-K 2026-07) |
| ai_investment | AMZN | "suppliers for semiconductor products, including products related to artificial intelligence infrastructure such as graphics processing units" (10-K 2026-02). **넷 중 근거가 가장 약하다.** 설비투자 금액과 AI를 직접 잇는 문장은 찾지 못했다 |
| ai_investment | META | "our AI initiatives will require increased investment in infrastructure" (10-K 2026-01) |
| gpu_demand | NVDA | Data Center 플랫폼, GPU·가속 컴퓨팅 (10-K 2026-02) |
| gpu_demand | AMD | 데이터센터 매출 증가를 "AMD Instinct MI350 Series GPUs" 수요로 설명 (10-K/A 2026-02) |
| gpu_demand | AVGO | "AI semiconductor solutions include custom accelerators or XPUs" (10-K 2025-12) |
| gpu_demand | TSM | "AI accelerators, including AI GPUs and AI ASICs" 생산 (20-F 2026-04) |
| hbm_supply·hbm_demand | MU | HBM3E·HBM4 생산, "Cloud servers supporting AI… require significantly increasing quantities of DRAM, including HBM" (10-K 2026-10) |
| memory_price | MU | 메모리 수요가 줄면 "average selling prices for our products could decline materially" (10-K 2026-10) |
| semi_earnings | NVDA, AMD, AVGO, MU, SNDK, TSM, INTC | 각 10-K·20-F에서 반도체 설계·생산·판매 기업이라고 밝힘 |

## 넣지 않은 연결 (근거 부족, 팀 검토 안건)

| 후보 | 넣지 않은 이유 |
|---|---|
| INTC ↔ gpu_demand | Gaudi AI 가속기는 재고 손실 문맥에서만 나오고 주력이라는 문장은 없다 |
| ARM ↔ gpu_demand, semi_earnings | 칩이 아니라 설계 IP 라이선스 회사다. 공시에도 "AI 가속기로 일이 옮겨 가면 CPU 시장이 줄 수 있다"는 반대 방향 위험이 있다 |
| LRCX ↔ hbm_demand, semi_earnings | HBM 적층용 장비를 판다(10-K). 반도체 **장비** 회사라 수요·실적 경로가 한 단계 더 간접적이다 |
| SNDK ↔ memory_price | 이 개념은 범용 **D램** 가격이다. 샌디스크는 낸드 회사이고, 공시에서 D램은 사 오는 부품(원가)으로 나온다. 방향이 반대일 수 있다 |
| NVDA·AMD ↔ hbm_demand | HBM을 사는 쪽이다(NVDA 10-K: "We purchase memory from SK Hynix, Micron, Samsung"). 붙이면 "HBM 수요 = 엔비디아에 좋음"으로 잘못 읽힐 수 있다 |
| COHR, LITE ↔ gpu_demand | AI 데이터센터용 광부품·레이저를 판다. 반도체 수요 개념과 직접 맞는 개념이 사전에 없다 |
| 한국 종목 (SK하이닉스 000660, 삼성전자 005930) | 이번 범위는 탭 2 미국 21종목이다. 형식 검사는 이미 KR을 지원한다 |
| 금리 개념 7개, 차트 읽기 개념 4개 | 금리는 특정 회사보다 시장 전체에 걸린 개념이고, 차트 읽기는 회사와 무관한 신호다 |
| AAPL, PANW, NET, LLY, NTRA, KO | 사전의 AI·반도체 개념과 맞는 사업이 아니다 |
