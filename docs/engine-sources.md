# P2 수치·구현 근거

- Liljegren 논문: https://doi.org/10.1080/15459620802310770 (서지: https://www.osti.gov/biblio/936511)
- 선택: lwbgt 1.0.1 공개 구현. Windows wheel 설치 및 함수 호출 가능. 직접 포팅은 하지 않음.
- 라이선스: Apache-2.0 및 UChicago Argonne WBGT v1.1. docs/licenses/ 원문·NOTICE 보존.
- 출처: https://github.com/zyf0717/lwbgt/blob/v1.0.1/LICENSING.md
- PyWBGT(QINQINKONG)의 NC-SA 조건 대신 위 구현을 선택.
- pvlib: https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.location.Location.get_clearsky.html
- 정책: https://www.wbgt.env.go.jp/en/sp/wbgt.php 및 https://media.fifpro.org/media/ltio1czh/heat-guidelines_en-1.pdf
- 2026-10-01 원문과 경계를 대조. YAML에는 요구대로 원문 대조 필요 표시 유지.
- 기압 1013.25hPa·고도 0m·풍속 10m는 명시적 스크리닝 가정. 실제 자료 메타데이터 확인 필요.
- ASOS 하늘상태 누락 시 운량 0.7 가정. 관측 일사량 있으면 우선. 실제 누락 정책은 표본 확인 후 개선.
- 실내/전체 그늘은 직접 일사 0, 부분 그늘은 보수적으로 전체 일사. 그늘 하락 계수는 임의로 추가하지 않음.
- 표면별 WBGT 추가 보정 기본 0. 인조잔디 표면온도 주의는 별도 안내.
- 현장 실측은 같은 출처(mock 여부) 및 1시간 이내 기준치와 차이를 구하고 이후 중앙값을 보정.
  기본 범위는 줄이지 않으며 실측 오차가 크면 넓힌다. 정식 통계 신뢰구간이 아님.
- 간이 폴백은 Stull 습구 근사 + 경험적 일사 보정이며 방법·사유에 간이 추정 표시.
- 실제 ASOS 샘플 미제공: 현재 PNG·MAE·편향은 합성 자료 실행 검증이다. 관측 검증 수용 항목은 보류.
