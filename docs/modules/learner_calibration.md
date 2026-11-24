> **초안 (Claude 작성, 2026-11-24).** 담당자 사람2가 읽고 고쳐서 확정한다.

# worker/learner/calibration.py (확신 보정)

- **한 줄 설명**: "안다고 생각함"(확실해요 / 헷갈려요)과 "실제로 맞힘"이 얼마나 맞는지 계산한다 (계획 2-5). DB를 모르는 순수 계산이고, 개수는 `learner/state.py`가 센다.
- **확률로 바꾸지 않은 이유 (계획 9장의 "아직 안 정한 것"에 대한 결정)**: 계획은 "확실해요 = 0.9, 헷갈려요 = 0.6" 같은 확률 변환을 예로 들었지만, 그 숫자는 우리가 정한 값이 된다. 확신이 두 단계뿐이라 정답/오답 × 확실/헷갈려요의 **2 × 2 표에서 바로 계산하는 지표**를 쓰면 임의의 숫자가 필요 없다. 그래서 확신 버튼에는 Brier 점수와 보정 곡선을 쓰지 않는다 (계획이 허용한 대안: "두 그룹의 실제 정답률만 비교").
- **입력**: `Table(sure_right, sure_wrong, unsure_right, unsure_wrong)`. 확실해요 + 맞힘, 확실해요 + 틀림(착각), 헷갈려요 + 맞힘(과소확신), 헷갈려요 + 틀림.
- **하는 일 (`summarize`)**:
  - `sensitivity` = 맞힌 답 중 확실해요 비율 ("아는 것을 안다고 했나"), `specificity` = 틀린 답 중 헷갈려요 비율 ("모르는 것을 모른다고 했나")
  - `illusion` = 틀린 답 중 확실해요 비율 (착각률, 1 − specificity). 가장 위험한 칸
  - `sure_accuracy` / `unsure_accuracy` = 확실해요 답의 정답률, 헷갈려요 답의 정답률. `gap` = 둘의 차이
  - `gamma` = (a·d − b·c) / (a·d + b·c). +1이면 확신이 정답을 완전히 가르고 0이면 무관
  - `bias` = 확실해요 비율 − 정답률. 양수면 과신, 음수면 과소확신
  - `enough` = 답이 20개 이상인가
- **출력**: 위 지표의 dict. 분모가 0인 지표는 None (예: 틀린 답이 없으면 착각률을 알 수 없다).
- **손계산**: 답 20개 (9, 3, 3, 5)면 sensitivity 9/12 = 0.75, specificity 5/8 = 0.625, 착각률 3/8 = 0.375, 확실해요 정답률 0.75, 헷갈려요 정답률 0.375, gamma (45 − 9) / (45 + 9) = 0.667, bias (3 − 3) / 20 = 0.
- **근거**: sensitivity·specificity는 Schraw, Kuch & Gutierrez (2013, *Learning and Instruction* 24(1), 48–57). 2 × 2 표로 만드는 지표 10개를 비교했더니 이 두 개가 가장 잘 설명했다 (초록으로 확인). gamma는 Nelson (1984, *Psychological Bulletin* 95(1), 109–133)이 확신과 정답의 관계를 보는 지표로 권했다 (초록으로 확인. 이후 응답 편향에 영향받는다는 비판이 있다: Fleming & Lau 2014, *Frontiers in Human Neuroscience* 8:443). bias는 Schraw (2009, *Metacognition and Learning* 4)의 bias 지수를 두 단계 확신(확실 1, 헷갈려요 0)에 적용한 것이다 (**원문 수식은 확인하지 못했다. 발표 전 확인 필요**). "확실해요인데 틀림"을 가장 위험하게 보는 것은 과잉 수정 효과(Butterfield & Metcalfe 2001, 계획 참고 문헌).
- **`brier(probs, outcomes)`**: 확률 예측과 실제 결과를 비교하는 Brier 점수 (Brier 1950). 확신 버튼이 아니라 BKT 알 확률 같은 확률 예측을 평가할 때 쓴다 (사람1의 가상 학습자 평가에서 쓸 수 있다).
- **DB·API 쪽 (`state.confidence_table`, `state.calibration_report`, `GET /learner/calibration/{user_id}`)**: 본 문제(`user_answers`)와 개념 퀴즈(`concept_answers`)에서 확신을 누른 답만 센다. 보고서는 `all`(전체), `recent`(최근 30일), `earlier`(그 전), `sure_wrong_concepts`(확실해요라고 했는데 틀렸고 아직 다시 맞히지 못한 개념)를 준다. `recent`와 `earlier`의 bias·착각률을 비교해 "과신이 줄었나"를 본다.
- **주의할 점**: 20개 미만이면 `enough = false`이고, 비율이 한두 문제에 크게 흔들리니 화면은 숫자 대신 "아직 부족"을 보여 준다. 20이라는 기준은 계획의 "20~30개"에서 온 값이고 문헌 값이 아니다. 최근 30일도 계획의 "한 달 전보다"에서 온 값이다. 판단해보기는 확신을 누르지 않으니 빠진다. 문제가 쉬우면 맞힌 답이 많아 지표가 좋아 보이므로, 사용자끼리 비교하기보다 한 사람의 시간에 따른 변화를 보는 데 쓴다. 마이페이지 화면(2-7)과 Spring 연결은 아직 없다.
- **테스트**: `cd worker && python -m pytest tests/test_calibration.py -q` (9개: 20개 손계산, 완벽한 구분, 과신·과소확신의 bias 부호, 확신과 정답이 무관하면 gamma 0, 거꾸로면 음수, 빈 칸은 None, 20개 기준, 음수 거부, Brier 손계산). DB 쪽은 `test_learner_state.py`에 2개(두 답 테이블 합산·확신 없는 답 제외, 최근과 이전 나누기), API는 `test_learner_api.py`에 1개.
