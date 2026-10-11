> **초안 (Claude 작성, 2026-10-11).** 담당자 B가 읽고 고쳐서 확정한다.

# worker/scripts/check_etf_holdings.py

- **한 줄 설명**: 액티브 ETF 2개(TIME `426030`, KoAct `0015B0`)의 구성종목을 pykrx로 받아 형식을 출력하는 1회성 확인 스크립트.
- **입력**: `.env` 의 `KRX_ID`, `KRX_PW` (data.krx.co.kr 일반 회원 계정), 조회 날짜(인자로 주거나 기본값: 최근 거래일, 9/30, 6/30).
- **하는 일**: 날짜별로 구성종목을 받아 전체 줄 수, 주식 줄 수, 주식이 아닌 줄(현금·선물), 소수 수량 줄 수, 코드 예시를 보여준다. 어떻게 저장할지는 판단하지 않는다.
- **출력**: 화면 출력만 (DB·파일에 쓰지 않음).
- **주의할 점**: KRX 로그인이 없으면 pykrx가 빈 결과를 돌려준다. 주식이 아닌 줄은 "이름에 현금이 있거나 코드가 6자리가 아님"으로 가린다. 확인 결과는 사람이 docs/findings.md 에 정리한다.
- **테스트**: 1회성 스크립트라 pytest 없음. 확인 방법은 `cd worker && python scripts/check_etf_holdings.py` 실행 → 두 ETF 모두 날짜마다 "전체 N줄"이 나오는지. Windows에서 한글이 깨지면 PowerShell에서 `$env:PYTHONUTF8=1` 후 실행.
