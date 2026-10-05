# 발표 출처와 확인 상태

정책·구현 근거2026-10-01 확인, 실제 관측 해석·분석2026-10-02 추가, 계산 검증의 발표 반영2026-10-05. 같은 날 공모요강과 아래 두 대회 서비스의 공식 공개 기능을 새로 확인했다. 기존 정책·논문 전체를 다시 검증한 것은 아니다. 아래 링크를 마지막 출처 화면/부록에 포함한다.

| 근거 | 출처 | 발표 사용 범위 |
|---|---|---|
| 일반 운동 WBGT 단계 | [일본 환경성](https://www.wbgt.env.go.jp/en/sp/wbgt.php) | 21/25/28/31℃ 경계와 운동 조정. 국내 유소년 적용은 자문 필요 |
| 축구 냉각·연기 권고 | [FIFPRO 공개 지침 p.2](https://media.fifpro.org/media/ltio1czh/heat-guidelines_en-1.pdf) | WBGT26℃ 초과 냉각,28℃ 초과 지연/연기. 프로 축구 지침의 적용 맥락 표시 |
| Liljegren 모델 | [2008 논문 DOI](https://doi.org/10.1080/15459620802310770) | 표준 기상 입력을 쓰는 물리 모델 서지. 논문 성능을 본 서비스 정확도로 전용하지 않음 |
| 공개 구현·라이선스 | [lwbgt1.0.1 LICENSING](https://github.com/zyf0717/lwbgt/blob/v1.0.1/LICENSING.md) | 공개 구현 선택, Apache-2.0/Argonne WBGT1.1. 직접 포팅 아님 |
| 태양·맑은하늘 모델 | [pvlib 공식 문서](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.location.Location.get_clearsky.html) | 기존 추정식을 동일1시간 구간으로 적분해 실제 일사 비교. 현장 WBGT 검증과 구분 |
| 실제 기상 관측 입력 | 제공 ASOS 활용가이드·수원119 수집 JSON·[샘플 해석 근거](../kma/asos-observation-evidence.md) | 2026-07-01~08-31·62일·1488시간, 필드·단위·원본 지문 |
| 관측 시각·시간 구간 | [기상청 ASOS 설명](https://apihub.kma.go.kr/apiList.do?apiSeq=2), [국립기상과학원 관측 연구 §2.2~2.3](https://doi.org/10.14191/Atmos.2020.30.1.059) | KST·이전1시간 대표값·같은 시간 구간 비교. 다른 API 주소/변수는 사용하지 않음 |
| 실제 실행 결과 | [실제 일사 비교](../real-data/a2-solar.md), [62일 재현](../real-data/a3-replays.md) | 관측927시간 MAE62.67W/m²·편향+6.74W/m², 결측561시간 제외. 추천7월10일15배정/0연기6114→4319 |
| 최고값 계산 검증·조건부 결론 | [WBGT 검증 보고서](../wbgt-sanity-report.md), [피크 계산](../wbgt-sanity/peak-traces.json) | 관측 입력 기반 모델 추정과 경기장 보정·범위를 구분. 가상12팀·15경기에서46일 일부 연기, 0경기 배정일3일(8월 4·5·6일). 실제 대회 일반의 개최 불가 일수 아님 |
| 가정별 민감도 | [분석 결과](../wbgt-sanity/sensitivity-results.json) | 보정0℃에서46→30일, 중앙값 판정까지 결합하면46→15일. 분석용 비교이며 정책/기본값 변경 근거 아님. ±1℃는 가상 편차로 관측 오차 범위 아님 |
| 경기장 보정의 근거·한계 | [기준 명세](../spec.md), [계산 검증 보고서](../wbgt-sanity-report.md) | 보정 +2.5℃는 해외 연구 기반 설계 가정으로, 국내 구장 검증과 전문가 검토가 필요. 현장 대조·인터뷰·자문 미수행 |
| 공모전 제출물·일정 | [공식 공모요강](https://ggsports.spectory.net/innovation/contest?bno=60730) | 시연 포함7분 발표, 서비스 링크/활용 영상 등. 접수 전 변경 여부 재확인 |
| 대진·기록 기능 비교 | [스파인더 공식 FAQ](https://www.sfinder.co.kr/faq/list) | 대진 자동화·기록 관리가 기존 기능임을 확인. 다른 기능의 부재나 동일 조건 성능 비교는 주장하지 않음 |
| 진행 순서 기능 비교 | [스포츠프리즘 공식 소개](https://www.sportsprism.net/about/company-intro) | 순서 최적화가 기존 공개 기능임을 확인. 업체 홍보 성능 수치는 검증하지 않아 인용하지 않음 |

프로젝트 구현과 실제 실행 근거: ../p2-report.md, ../p3-report.md, ../p4-report.md, ../p5-report.md.
라이선스 원문: ../licenses/, ../../backend/assets/fonts/OFL.txt.
Argonne 고지: “This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the Department of Energy.”

## 아직 발표 근거로 쓰지 않을 것

- 현장 WBGT 오차·건강 효과·실제 도입/인터뷰: 미검증(관측 입력의 가상 대회 재현과 구분)
- 국내 최초·경쟁사 폭염 기능 없음·검증된 시장 규모/가격: 근거 없음. 일부 공식 대진/기록/순서 기능만 확인
- 해외 의무화 범위·일정 등 시사 주장: 이번 원고에서 제외, 사용할 때 공식 원문 추가 검증
- 영상 기반 개인 부하: 연구 단계, 아마추어 영상 품질 미통과
- OSTI 서지 페이지는 이번 재조회에서502로 응답하여 DOI를 서지 링크로 유지

정책 수치·기본 보정·불확실성 범위는 명세 그대로 유지했다. 새 통계나 수익 수치를 만들어 넣지 않았다.
