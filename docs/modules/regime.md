> **초안 (Claude 작성, 2026-11-19, #174).** 담당자 B가 읽고 고쳐서 확정한다.

# worker/concepts/regime.py

- **한 줄 설명**: 삼의 법칙(Sahm rule) 지표로 "지금 경기 국면"(normal / recession)을 코드가 정해, 개념 사전의 국면별 조건부 연결(#158)이 탭 1 출제·검증에 실제로 쓰이게 한다.
- **입력**: FRED `SAHMREALTIME`(삼의 법칙 실시간 지표, 매달 숫자 하나, %p). FinanceDataReader(`FRED:SAHMREALTIME`)로 받고 키는 필요 없다(collectors/sources.py의 정책금리와 같은 방법). 기준일(`as_of`, 출제에서는 카드 날짜).
- **하는 일**:
  - 기준일이 속한 달보다 **앞 달**의 값 중 가장 최근 것을 쓴다. 그달 값은 다음 달 초에 나오므로, 같은 달 값을 쓰면 지난 날짜로 카드를 다시 만들 때 그때는 몰랐던 값을 보게 된다.
  - 값(소수 둘째 자리로 반올림) ≥ 0.5면 `recession`, 아니면 `normal`(`regime_of`). LLM은 판단하지 않는다.
  - 지표를 받지 못하거나 앞 달 값이 없으면 `normal`로 두고 까닭을 `source`에 남긴다. 국면 때문에 출제가 멈추지 않게 하려는 것이다.
  - `regime_for_month(year, month)`는 달마다 한 번만 FRED를 부른다(같은 달이면 판정이 같음). 실패한 결과도 그 실행 동안은 다시 묻지 않아 카드마다 국면이 달라지지 않는다.
- **출력**: `Regime(name, sahm, observed, source)`. 예: `Regime("normal", 0.0, "2026-10-01", "FRED SAHMREALTIME")`. `to_json()`은 카드 `cards.model_info.regime`에 그대로 저장된다. `prompt_note()`는 침체일 때 출제 에이전트에게 알려 줄 한 줄(평상시면 None).
- **쓰는 곳**:
  - `generate/compose.py`: 카드 날짜의 달로 국면을 정해 `ToolContext.regime`에 넣고, 마지막 검증(`verify(..., regime=)`)도 그 국면으로 한다. 침체면 사용자 메시지에 `prompt_note`를 붙인다. 저장할 때 `model_info.regime`에 근거를 남긴다.
  - `generate/tools.py`: `find_concept_path`·`validate_causal_order`가 `ctx.regime`으로 계산하고, 경로 찾기 결과에 `regime`을 적는다(에이전트 입력이 아니라 코드가 넣는 값).
  - `validate/validators.py`: `verify(quiz, text, g, regime=)`. 주지 않으면 평상시라 예전과 같다.
- **주의할 점**:
  - **미국 지표다.** 지금 사전의 조건부 연결(경기 침체 때 국채 금리 → 성장주 가치평가 ▲, 곧 금리 ▼ → 성장주 ▼)은 미국 성장주 이야기라 맞지만, 국내 뉴스 카드에도 같은 국면을 쓴다.
  - **헛신호가 있다.** 2024년 7~9월 지표가 0.53·0.57·0.50으로 0.5를 넘었지만 실제 침체(NBER 판정)로 이어지지 않았다. 이 기준으로는 그때 카드가 경기 침체 국면으로 나간다.
  - 탭 2 이유(reasons)는 이번에 넣지 않았다. 큰손 기준일(분기 말)의 국면을 따로 정해야 해서 다음 작업으로 둔다.
  - 테스트는 FRED를 부르지 않는다. `tests/conftest.py`가 모든 테스트에서 `fetch_sahm`을 가짜(지표 0.00 = 평상시)로 바꿔 끼운다.
- **결과 (2026-11-19 실제 FRED)**: 오늘 기준 2026-10 = 0.00 → normal. 2024-09-15 기준 2024-08 = 0.57 → recession. 2024-11-15 기준 2024-10 = 0.43 → normal.
- **테스트**: `cd worker && python -m pytest tests/test_regime.py -q` (경계 0.49 / 0.50 / float 0.5000000000000001 / 음수, 앞 달 값만 쓰기(10/15 카드는 9월 값), 받기 실패·값 없음은 평상시와 까닭, 달마다 FRED 한 번, 침체일 때만 프롬프트 한 줄, 검증기: 기준금리 인하 → 국채 금리 → 성장주 평상시 ▲ 통과·경기 침체에서는 방향 다름, 도구가 ctx 국면으로 계산). `tests/test_compose.py`에 국면이 도구·프롬프트·model_info로 가는지, 기본은 평상시라 프롬프트가 예전 그대로인지. 실행 확인: `python -m concepts.regime`, `python -m concepts.regime --date 2024-09-15`.
