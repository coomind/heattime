# 의존성 라이선스와 자료 출처

설치된 패키지 정보에서 자동으로 뽑은 목록입니다(`scripts/package_submission.py`). 전이 의존성은 각 패키지의 라이선스를 따릅니다.

| 구분 | 이름 | 버전 | 라이선스 | 용도 |
|---|---|---|---|---|
| Python | lwbgt | 1.0.1 | Apache-2.0 AND LicenseRef-UChicago-Argonne-WBGT-1.1 | WBGT 계산 (Liljegren 모델 공개 구현). Apache-2.0과 Argonne WBGT 1.1 고지 포함 |
| Python | ortools | 9.15.6755 | Apache Software License | 경기 재편성 최적화 (CP-SAT) |
| Python | pvlib | 0.16.1 | BSD-3-Clause | 태양 위치와 맑은 하늘 일사 추정 |
| Python | PyYAML | 6.0.3 | MIT License |  |
| Python | matplotlib | 3.11.2 | Python Software Foundation License |  |
| Python | fastapi | 0.142.2 | MIT | 백엔드 API |
| Python | uvicorn | 0.54.0 | BSD-3-Clause |  |
| Python | reportlab | 5.0.1 | BSD License | 운영 기록 PDF |
| Python | httpx | 0.28.1 | BSD License |  |
| npm | @fontsource/ibm-plex-mono | 5.3.0 | OFL-1.1 | 숫자 서체 |
| npm | @fontsource/ibm-plex-sans-kr | 5.3.0 | OFL-1.1 | 화면 한글 서체 원본 (서브셋으로 포함) |
| npm | react | 19.3.0 | MIT | 화면 |
| npm | react-dom | 19.3.0 | MIT |  |
| npm | recharts | 3.10.1 | MIT | 그래프 |
| npm | @axe-core/playwright | 4.14.0 | MPL-2.0 | 개발·시험용 |
| npm | @playwright/test | 1.63.0 | Apache-2.0 | 개발·시험용 |
| npm | @vitejs/plugin-react | 4.7.0 | MIT | 개발·시험용 |
| npm | vite | 7.3.6 | MIT | 개발·시험용 |
| 서체 | IBM Plex Sans KR (서브셋) | @fontsource 5.x | OFL-1.1 | 화면 글꼴, KS X 1001 한글과 앱 문구만 남긴 WOFF |
| 서체 | IBM Plex Mono | @fontsource 5.x | OFL-1.1 | 숫자 글꼴 |
| 서체 | NanumGothic | backend/assets/fonts | OFL-1.1 | PDF 한글 글꼴 |

## 고지

- This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the Department of Energy.
- 라이선스 원문은 이 폴더의 txt 파일에 있습니다.

## 기상 자료 출처

- 기상청 지상(종관, ASOS) 시간자료 조회서비스(공공데이터포털 오픈API), 수원 지점 119, 2026-07-01~2026-08-31 시간자료. 앱의 시연 장면은 이 관측값으로 계산한 WBGT 추정을 담고 있습니다.
- 최신 관측 연결 시험(1회)은 기상청 API허브 방재기상관측(AWS) 분 자료를 사용했습니다.
- 출처 표기: "자료: 기상청". 공공데이터포털의 이용허락범위는 제출 전에 다시 확인해야 합니다(이 저장소에는 확인 기록이 없습니다).
- 원본 응답, 정규화한 관측 파일, 기상청 활용가이드 문서는 재배포 조건이 확인되지 않아 소스 압축에서 뺐습니다.
