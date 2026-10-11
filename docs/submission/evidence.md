# 제출 주장과 증거 연결

**2026-10-11 재계산: 일사 구간 정렬·판정값 0.1℃ 반올림·동점 처리 고정 후 전 수치 재생성**. 아래 수치는 현재 엔진의 결과다. 같은 입력의16팀·2일31구간은 단순583건 대비 엔진593건(재실행592건·7월17~18일 FEASIBLE 27→26),12팀·1일62일은555배정이며, 첫62일 실행은 이 Windows 개발 PC에서62/62 CP-SAT OPTIMAL이었고 같은 입력의 전체 재실행에서는7/20이10초 제한에 도달해 FEASIBLE(일정 동일)로 끝났다. 다른 실행 환경에서는 OPTIMAL/FEASIBLE 표시가 다를 수 있어 "62일 모두 최적 증명"을 조건 없이 단정하지 않는다.18개 FEASIBLE 구간의 최적성은 미확정이다. 재계산 전 고정 결과(596/598/608·562·61OPTIMAL/1FEASIBLE)는 [수정 보고](../review-fix-report.md)와 [재계산 보고](../recalc-2026-10-11.md)에 보존한다. 현재 후보 비교는 단순 대안 이상의 배정을 선택하는 규칙이며 최적화가 독립적으로 항상 우월하다는 주장을 하지 않는다.


숫자는 동일 조건의 원본 결과를 확인한 경우만 쓴다. 코드 테스트 통과와 현장 정확도는 별개다.

이번 제출의 주된 증거는 실측 없이 재현 가능한 기술 검증이다. 현장 기록 확보를 제출 전 필수 과제로 두지 않는다. 수상권·현장 정확도·효용을 입증했다고 표현하지 않는다.

2026-10-06: [기술 증거 묶음](../competition-evidence/proof-pack.md)과 [기계 판독 주장 대장](../competition-evidence/verified-claims.json)이 각 분석 수치·원본 지문·전체 테스트 영수증을 연결한다. 실제/가상 업무 비교·현장 대조·검토 제외 기능은 [검사 보고](../validation-feature-report.md)와 [최신 입력 연결](../live-reference-report.md)에 있다. 실제 운영자·현장 자료는 아직 없으므로 기능 시험을 고객 성과나 수상 가능성으로 집계하지 않는다.

| 제출 주장 | 직접 근거 | 주장할 수 없는 내용 |
|---|---|---|
| 날짜별 유리한 단순4종 대비552→555건·완전 배정15→15일·공통 열 노출4.15% 감소 | [모든62일 원자료](../competition-evidence/no-field-analysis.json), [검사와 해석](../no-field-analysis-report.md) | 사람·경쟁사·건강 효과 우위, 모든 단순 방법 대비 우위 |
| 고정 제안/승인 일정의 추정 이동·자료 누락 검토 | [읽기 전용 기능](../plan-review-report.md), backend/plan_review.py, tests/test_no_field.py | 실제 오차 범위·발생 확률·재최적화 후 개최 불가 일수 |
|16팀·2일31구간에 확대하여 한계를 확인 | [규모 검증 보고](../tournament-scale-report.md), [재계산 원자료](../competition-evidence/tournament-scale-analysis.json): 단순583건 대비 엔진593건, 재실행592건 | 대진 일반의 배정 우위; 18개 FEASIBLE 연기의 불가피성·재실행 동일성 |
| 폭염 판정·대진 제약·승인·기록이 한 흐름으로 동작 | [P3](../p3-report.md), [P4](../p4-report.md), frontend/e2e의 기존 전체 흐름 검사 | 실제 운영자가 사용했다는 주장 |
| 관측 입력의 가상 대회 재현 | [관측 필드·단위·지문](../kma/asos-observation-evidence.md), [62일 원본](../real-data/replay-results.json) | 구장3곳을 각각 관측했다는 주장 |
| 8월10일 13배정/2연기(semi2·final)·원래 중지14경기 중13경기 재배정 | 같은 원본의 hot_candidates 중 2026-08-10 행(31℃ 이상 규칙 1순위; 이후8월14일·7월14일·8월9일·8월11일), [시연일 선정](../real-data/demo-days.md), [5회 반복 확인](../real-data/demo-day-check.json) | 실제13경기를 살렸다거나 안전을 보장했다는 주장; 다른 환경에서도 매번 OPTIMAL이라는 주장 |
| 공통13경기6442→3879·2563점·39.79% 감소 | 2026-08-10 행의 original_heat / proposed_heat / common_count; frontend/tests/schedule-outcome.test.js | 연기 경기를 빼고 전체 비용을 줄였다는 주장, 사고 감소율 |
| 추정 중앙 최고31.274℃·범위29.774~32.774℃(13시 구장 A) | 같은 후보의 max_wbgt_c와 관측 스냅샷 approved.risks의 최고 중앙값 행 wbgt_low_c / wbgt_high_c | 현장 WBGT 실측 |
| 극한일8월8일 7배정/8연기(35.4℃) | days의 2026-08-08 행, data/output/real/2026-08-08.json, 같은 5회 반복 확인 | 더운 날 경기 개최 보장, 실제 대회의 연기 필요 일수 |
| 최고기온33℃ 이상인 날은 모두8경기 이상 연기 | days의 max_ta_c>=33 행; tests/test_real_replay_results.py | 실제 대회 일반의 개최 불가 조건 |
| 62일 중47일의 동일일15경기 전체 배정 실패 | [WBGT 보고](../wbgt-sanity-report.md), [민감도 원본 baseline](../wbgt-sanity/sensitivity-results.json) | 실제 대회 일반의 개최 불가 일수; 0배정일은10일과 별도 |
| 사전 계산 관측 시연은 오프라인에서도 동작 | frontend/e2e/observed.spec.js 및 outcome.spec.js의 API 요청0·오프라인 재로딩 검사 | 최초 방문도 서버가 전혀 필요 없다는 주장 |
| 대진·기록 자동화만으로는 신규성 주장 부족 | [공식 기능 조사](competition-fit.md) | 경쟁사에 폭염 기능이 없다는 단정, 동일 성능 비교 |
| 인터뷰·가격·현장 검증은 미수행 로드맵 | [계획](validation-plan.md) | 계획을 완료 실적이나 이번 제출 전 완료 약속으로 표현 |
| 기존 약한 탐욕 대비 배정합계66건 증가·완전 배정0→15일(참고) | [전체 비교](../competition-evidence/method-comparison.json), [고정 제안](../competition-evidence/frozen-solutions.json), [해석](../competition-evidence/method-comparison.md) | 주된 우위로 과장, 사람·경쟁 제품 대비 우위, 현장에서 살린 경기 수; 공통 점수2.90% 증가도 공개 |
| 모든62일 결과·경기별 변경 내역을 오프라인으로 읽을 수 있음 | frontend/e2e/evidence.spec.js와 새 단위 검사 | 현재 선택한 설정을 다시 계산한 전체기간 결과라는 주장 |
| 제안/승인 제약 근거·입력/보정 이력·CSV 미리보기 | [세 개선 기능 검증](../feature-implementation-report.md), 관련 단위/데스크톱/모바일 검사 | 실제 운영자의 이해도·업무 절감 실측 |
| 실제 AWS 119 자료 수신·공식 필드·기존 계산 확인 | [실제 연결 검증](../live-connection-report.md), [성공 기록](../kma/live-connection-verification.json) | 기본 10초 안정성 확보(4회 시간 초과), 현장 WBGT 측정·미래 예보·주간 폭염 정확도 |

소프트웨어의 새 결과 요약은 기존 proposal·recommendations만 읽는다. 계산 엔진·설정·정책·스냅샷의 원본 수치를 바꾸지 않는다. 승인 전·승인됨·수정안 승인·거절을 구분하며 수정안 승인 시 자동 제안 수치와 수정된 승인 기록을 구분해 표시한다.

자동 검사: 프로젝트 루트의 `scripts/check_presentation.py`로 기존 발표 숫자·전체 가정·화면 분리·7분 시간표를 검사한다. frontend의 `npm run test:unit`로 공통 경기·연기 별도·점수 증가·0분모를 검사하고 `npm run test:e2e:repeat`로 화면 흐름을 반복한다. 실행 결과는 [개선 보고](../competition-improvement-report.md)에 기록한다.
