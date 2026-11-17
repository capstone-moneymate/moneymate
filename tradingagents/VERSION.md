# TradingAgents 버전 (설치 후 확인한 값)

확인일: 2026-11-16, 확인 방법: `pip show tradingagents`, 설치 패키지의 `direct_url.json`, 저장소 `pyproject.toml`

| 항목 | 값 |
| :--- | :--- |
| 패키지 | tradingagents **0.7.1** (`pip show tradingagents`, `tradingagents.__version__`) |
| 설치 출처 | GitHub `TauricResearch/TradingAgents` 태그 `v0.7.1`. PyPI 에는 없음 (pypi.org/pypi/tradingagents → 404) |
| 커밋 | `3e44faafa042daf953f6ec2422ae36bb1fd4f50f` |
| pyproject.toml | `version` 은 dynamic (`tradingagents.__version__`), `requires-python = ">=3.11"` |
| Python | 3.12.10 (worker 와 분리된 `tradingagents/.venv`) |
| 주요 의존성 | langgraph 1.2.22, langchain-core 1.8.1, langchain-anthropic 1.7.10, anthropic 2.8.0, yfinance 1.8.0 |
| 라이선스 | Apache-2.0 |

검토 문서 두 곳의 값(0.6.0 / v0.3.1)은 모두 설치본과 다르다. 이 표의 값으로 고정한다.

## Anthropic 모델 목록 (설치본 `tradingagents/llm_clients/model_catalog.py`)

| 등급 | 모델 id |
| :--- | :--- |
| quick | `claude-sonnet-5`, `claude-haiku-4-5` |
| deep | `claude-opus-5-5`, `claude-fable-5-1`, `claude-sonnet-5` |

시험에는 가장 싼 조합 quick `claude-haiku-4-5`, deep `claude-sonnet-5` 를 쓴다 (`run_report.py` 가 실행 전에 목록에 있는지 검사).
