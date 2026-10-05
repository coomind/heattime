# 제출 주장과 증거 연결

숫자는 동일 조건의 원본 결과를 확인한 경우만 쓴다. 코드 테스트 통과와 현장 정확도는 별개다.

| 제출 주장 | 직접 근거 | 주장할 수 없는 내용 |
|---|---|---|
| 폭염 판정·대진 제약·승인·기록이 한 흐름으로 동작 | [P3](../p3-report.md), [P4](../p4-report.md), frontend/e2e의 기존 전체 흐름 검사 | 실제 운영자가 사용했다는 주장 |
| 관측 입력의 가상 대회 재현 | [관측 필드·단위·지문](../kma/asos-observation-evidence.md), [62일 원본](../real-data/replay-results.json) | 구장3곳을 각각 관측했다는 주장 |
| 7월10일 15배정/0연기·중지10경기 재배정 | 같은 원본의 candidates[0], [스냅샷 보고](../real-data/a5-snapshot.md) | 실제10경기를 살렸다거나 안전을 보장했다는 주장 |
| 공통15경기6114→4319·1795점·29.36% 감소 | candidates[0].original_heat / proposed_heat / common_count; frontend/tests/schedule-outcome.test.js | 연기 경기를 빼고 전체 비용을 줄였다는 주장, 사고 감소율 |
| 추정 중앙 최고32.043℃·범위30.543~33.543℃ | 같은 후보의 max_wbgt_c와 관측 스냅샷 approved.risks의 최고 중앙값 행 wbgt_low_c / wbgt_high_c | 현장 WBGT 실측 |
| 62일 중46일의 동일일15경기 전체 배정 실패 | [WBGT 보고](../wbgt-sanity-report.md), [민감도 원본 baseline](../wbgt-sanity/sensitivity-results.json) | 실제 대회 일반의 개최 불가 일수; 0배정일은3일과 별도 |
| 사전 계산 관측 시연은 오프라인에서도 동작 | frontend/e2e/observed.spec.js 및 outcome.spec.js의 API 요청0·오프라인 재로딩 검사 | 최초 방문도 서버가 전혀 필요 없다는 주장 |
| 대진·기록 자동화만으로는 신규성 주장 부족 | [공식 기능 조사](competition-fit.md) | 경쟁사에 폭염 기능이 없다는 단정, 동일 성능 비교 |
| 인터뷰·가격·현장 검증이 다음 단계 | [계획](validation-plan.md) | 계획을 완료 실적으로 표현 |
| 같은 제약 탐욕 대비 배정 합계56건 증가·완전 배정0→16일 | [전체 비교](../competition-evidence/method-comparison.json), [고정 제안](../competition-evidence/frozen-solutions.json), [해석](../competition-evidence/method-comparison.md) | 사람·경쟁 제품 대비 우위, 현장에서 살린 경기 수; 공통 점수1.39% 증가도 공개 |
| 모든62일 결과·경기별 변경 내역을 오프라인으로 읽을 수 있음 | frontend/e2e/evidence.spec.js와 새 단위 검사 | 현재 선택한 설정을 다시 계산한 전체기간 결과라는 주장 |
| 제안/승인 제약 근거·입력/보정 이력·CSV 미리보기 | [세 개선 기능 검증](../feature-implementation-report.md), 관련 단위/데스크톱/모바일 검사 | 실제 운영자의 이해도·업무 절감 실측 |
| 실제 AWS 119 자료 수신·공식 필드·기존 계산 확인 | [실제 연결 검증](../live-connection-report.md), [성공 기록](../kma/live-connection-verification.json) | 기본 10초 안정성 확보(4회 시간 초과), 현장 WBGT 측정·미래 예보·주간 폭염 정확도 |

소프트웨어의 새 결과 요약은 기존 proposal·recommendations만 읽는다. 계산 엔진·설정·정책·스냅샷의 원본 수치를 바꾸지 않는다. 승인 전·승인됨·수정안 승인·거절을 구분하며 수정안 승인 시 자동 제안 수치와 수정된 승인 기록을 구분해 표시한다.

자동 검사: 프로젝트 루트의 `scripts/check_presentation.py`로 기존 발표 숫자·전체 가정·화면 분리·7분 시간표를 검사한다. frontend의 `npm run test:unit`로 공통 경기·연기 별도·점수 증가·0분모를 검사하고 `npm run test:e2e:repeat`로 화면 흐름을 반복한다. 실행 결과는 [개선 보고](../competition-improvement-report.md)에 기록한다.
