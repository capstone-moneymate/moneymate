> **초안** 담당자 B가 정리하고, 싱크에서 팀 검토 후 확정한다.

# 개념 사전 초안 (db/seeds/concepts.csv, causal_edges.csv)

- **한 줄 설명**: 인과 뼈대의 기준이 되는 개념 17개와 개념 사이의 연결(올리는 힘 / 누르는 힘) 19개.
- **쓰는 곳**: 탭1 인과 순서 퀴즈 정답, 탭2 카드 ② 이유의 인과 뼈대, 탭3 인과 지도. LLM은 뉴스에서 시작 개념(`id`)만 고르고, 경로는 이 연결을 따라 코드가 찾는다.
- **적재**: 4주차 전에 `worker/concepts/loader.py`(B)가 CSV → `concepts`, `causal_edges` 테이블로 넣는다.

## CSV 형식

| 파일 | 컬럼 | 규칙 |
| --- | --- | --- |
| concepts.csv | `id,name,theme,kind,aliases` | `id`는 영문 소문자+밑줄. `aliases`는 `;`로 구분 (DB에서는 `TEXT[]`) |
| causal_edges.csv | `from_concept,to_concept,force_dir,note` | `force_dir`는 `up`(올리는 힘) / `down`(누르는 힘). "from이 커지면 to를 올린다/누른다"로 읽는다 |

`kind`는 4가지: `event`(사건) / `indicator`(지표) / `outcome`(결과) / `signal`(차트 신호)

## 개념 17개

| 테마 | 개념 |
| --- | --- |
| 금리 (7) | 기준금리 인상 `rate_hike` · 인하 `rate_cut` · 동결 `rate_hold` · 물가 상승 `inflation` · 국채 금리 `bond_yield` · 은행 예대마진 `bank_margin` · 성장주 가치평가 `growth_valuation` |
| AI·반도체 (6) | AI 데이터센터 투자 `ai_investment` · AI 반도체 수요 `gpu_demand` · HBM 공급 확대 `hbm_supply` · HBM 수요 `hbm_demand` · 메모리 반도체 가격 `memory_price` · 반도체 기업 실적 `semi_earnings` |
| 차트 읽기 (4) | 거래량 급증 `volume_spike` · RSI 과매수 `rsi_overbought` · 이동평균선 돌파 `ma_breakout` · 연속 상승 `consecutive_rise` |

## 연결 예시 (서비스흐름 2.2의 프로토타입 뉴스)

- **금리 4연속 동결 (유형 2)**: `rate_hold` → 예대마진 ▲ (은행) / 성장주 가치평가 ▼ (기술주) → "은행 vs 기술주 ETF 차트"로 이어짐
- **HBM4 공급 확대 (유형 3)**: `hbm_supply` → 반도체 기업 실적 ▲ / 메모리 가격 ▼
- **코스피 3거래일 연속 상승 (유형 1)**: `consecutive_rise`, `volume_spike` → 인과 뼈대 없이 차트 읽기

## 싱크에서 검토할 것

- [ ] **동결의 방향**: `rate_hold`는 그 자체로 미는 힘이 없다. "고금리 수준에서의 동결"로 보고 예대마진 ▲, 성장주 ▼로 둠. 동결 = "현재 수준 유지"로 보고 연결을 빼는 게 맞는지
- [ ] **HBM 공급 확대의 두 갈래**: 실적 ▲(판매량)와 메모리 가격 ▼(공급 증가)가 동시에 나간다. 학습자에게 헷갈리면 하나만 남길지
- [ ] **테마 연결**: `rate_cut → ai_investment`(조달 비용 하락)는 금리와 AI 테마를 잇는 유일한 연결. 인과 지도가 섬처럼 나뉘지 않게 둔 것인데, 근거가 약하면 뺄지
- [ ] **차트 읽기 개념에 연결이 없음**: 유형 1(뼈대 없음)용이라 의도한 것. 인과 지도(탭3)에 어떻게 보일지 C·B 합의
- [ ] **이름·별칭**: 뉴스 매칭(LLM)이 고르기 쉬운 이름인지, 빠진 별칭이 있는지
- [ ] **17개 → 30~50개 확장**: 다음에 넣을 후보 (예: 환율, 유가, 경기 침체, 실업률, 반도체 재고)
