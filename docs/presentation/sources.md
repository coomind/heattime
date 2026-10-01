# 발표 출처와 확인 상태

2026-10-01 확인. 본문에는 확인한 정책·구현 근거만 쓴다. 아래 링크를 마지막 출처 화면/부록에 포함한다.

| 근거 | 출처 | 발표 사용 범위 |
|---|---|---|
| 일반 운동 WBGT 단계 | [일본 환경성](https://www.wbgt.env.go.jp/en/sp/wbgt.php) | 21/25/28/31℃ 경계와 운동 조정. 국내 유소년 적용은 자문 필요 |
| 축구 냉각·연기 권고 | [FIFPRO 공개 지침 p.2](https://media.fifpro.org/media/ltio1czh/heat-guidelines_en-1.pdf) | WBGT26℃ 초과 냉각,28℃ 초과 지연/연기. 프로 축구 지침의 적용 맥락 표시 |
| Liljegren 모델 | [2008 논문 DOI](https://doi.org/10.1080/15459620802310770) | 표준 기상 입력을 쓰는 물리 모델 서지. 논문 성능을 본 서비스 정확도로 전용하지 않음 |
| 공개 구현·라이선스 | [lwbgt1.0.1 LICENSING](https://github.com/zyf0717/lwbgt/blob/v1.0.1/LICENSING.md) | 공개 구현 선택, Apache-2.0/Argonne WBGT1.1. 직접 포팅 아님 |
| 태양·맑은하늘 모델 | [pvlib 공식 문서](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.location.Location.get_clearsky.html) | 기술 흐름. 합성 일사 비교는 실제 관측 검증이 아님 |
| 공모전 제출물·일정 | [공식 공모요강](https://ggsports.spectory.net/innovation/contest?bno=60730) | 시연 포함7분 발표, 서비스 링크/활용 영상 등. 접수 전 변경 여부 재확인 |

프로젝트 구현과 실제 실행 근거: ../p2-report.md, ../p3-report.md, ../p4-report.md, ../p5-report.md.
라이선스 원문: ../licenses/, ../../backend/assets/fonts/OFL.txt.
Argonne 고지: “This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the Department of Energy.”

## 아직 발표 근거로 쓰지 않을 것

- 실제2026년 무더운 날 관측 재현, 현장 WBGT 오차·건강 효과, 실제 도입/인터뷰: 미검증
- 국내 최초·경쟁사 스포츠 기능 없음·검증된 시장 규모/가격: 조사 미완료
- 해외 의무화 범위·일정 등 시사 주장: 이번 원고에서 제외, 사용할 때 공식 원문 추가 검증
- 영상 기반 개인 부하: 연구 단계, 아마추어 영상 품질 미통과
- OSTI 서지 페이지는 이번 재조회에서502로 응답하여 DOI를 서지 링크로 유지

정책 수치·기본 보정·불확실성 범위는 명세 그대로 유지했다. 새 통계나 수익 수치를 만들어 넣지 않았다.
