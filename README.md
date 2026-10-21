# 히트타임 (HeatTime)

생활체육과 유소년 축구 대회 운영자를 위한 폭염 경기 운영 의사결정 보조 웹 서비스입니다. 기상 관측 자료로 구장과 시간마다 WBGT(습구흑구온도)를 추정하고, 경기별 권고(통상 진행, 쿨링브레이크, 시간 단축, 연기 후보)를 보여 준 뒤, 같은 제약 안에서 시간과 구장을 다시 짠 일정 제안을 만듭니다. 최종 판단은 운영자가 하고, 판단 사유와 근거가 운영 기록(PDF, CSV, JSON)으로 남습니다. 알림은 모의 발송이며 실제 문자나 카카오 메시지는 보내지 않습니다.

기준 명세는 [docs/spec.md](docs/spec.md), 작업 규칙은 [AGENTS.md](AGENTS.md)입니다. 2026 경기스포츠산업 공모전 출품작이며, 가상 대회로 검증한 시제품입니다. 현장 실측과 도입 실적은 없습니다.

## 시연 기준: 기상청 관측 스냅샷

- 기상: 기상청 지상(종관, ASOS) 시간자료, 수원 지점 119, 2026-07-01~2026-08-31 중 시연일의 관측값.
- 대회: 가상 U12 대회 12팀, 3구장, 15경기(조별 12경기, 준결승 2경기, 결승). 대회와 팀과 구장과 연락처는 모두 가상 예시입니다. 세 구장은 같은 관측소 자료를 함께 씁니다.
- 앱을 열면 첫 화면으로 8월 10일 장면의 대시보드가 바로 열립니다. 재현 화면에서 다른 장면을 고를 수 있습니다.

| 장면 | 주소 | 원래 일정 단계(0·1·2·3·4) | 재편성 결과 | 열 노출 점수(공통 경기) |
|---|---|---|---|---|
| 8월 10일: 재편성으로 전부 소화하는 날 | `#snapshot-observed` | 0·0·0·11·4 | 15경기 배정, 연기 없음 | 5,273 → 4,153 (15경기) |
| 8월 8일: 재편성해도 연기가 생기는 날 | `#snapshot-observed-0808` | 0·0·1·0·14 | 10경기 배정, 5경기 연기 | 5,993 → 2,648 (10경기) |
| 8월 8~9일: 같은 대회를 이틀 일정으로 다시 짠 경우 | `#snapshot-observed-0808-2day` | 0·0·1·0·14 | 15경기 배정, 연기 없음 | 8,608 → 3,681 (15경기) |

8월 8일에 연기 후보가 되는 경기는 1조 2경기, 4조 1경기, 준결승 1, 준결승 2, 결승입니다. 열 노출 점수는 일정 비교용 내부 점수이며 건강 효과나 사고 감소율이 아닙니다. 합성 날씨 장면(`#snapshot`)은 메뉴의 "합성 날씨(기능 시험용)"으로 남겨 두었습니다. 장면별 전체 수치는 `scripts/export_demo_numbers.py`가 만드는 `data/output/demo-numbers.md`에 있습니다.

## 판정 기준

- 판정값 = 관측 기반 WBGT 추정 + 구장 보정 2.5℃ = 중앙 추정(소수 첫째 자리 반올림). 이 값으로 단계를 정합니다(2026-10-21 작성자 결정, 이전에는 유소년을 추정 범위 상단으로 판정).
- 단계 경계는 21, 25, 28, 31℃입니다(일본 환경성 열사병 예방 정보, [원문](https://www.wbgt.env.go.jp/en/sp/wbgt.php)). 0단계는 화면에서 "통상 운영"으로 표시합니다.
- 추정 범위(중앙 ±1.5℃)는 불확실성을 보여 주려고 화면과 기록에 계속 표시하지만 판정에는 쓰지 않습니다. 현장에서 검증한 신뢰구간이 아닙니다.
- 구장 보정 2.5℃는 해외 연구를 바탕으로 한 설계 가정이며 국내 구장에서 검증하지 않았습니다. 전문가 자문이 필요합니다.
- 설정 위치: `backend/config/policies.yaml`(단계 경계, 원문 대조 표시, `age.upper_bound_groups: []`), 구장 보정은 구장 자료의 `field_offset_c`.

## 설치와 실행 (Windows PowerShell)

Python 3.13과 Node.js 22로 개발했습니다. 키나 `.env`가 없어도 시연할 수 있습니다. Vite는 `envDir:false`로 `.env`를 읽지 않습니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Push-Location frontend
npm ci
npm run build
Pop-Location
.\.venv\Scripts\python.exe -m backend.run --host 127.0.0.1 --port 8000
```

- http://127.0.0.1:8000 을 열면 8월 10일 관측 장면이 열립니다.
- http://127.0.0.1:8000/#live 는 서버와 연결된 재현 화면입니다. 기본 기상 자료는 기상청 관측(수원 119)이고, 날짜를 바꾸거나 "합성 날씨(기능 시험용)"을 고를 수 있습니다. 구장, 대회, 팀, 대진 등록과 CSV 가져오기, 수동 WBGT 입력도 여기서 합니다.
- SQLite는 `data/heattime.sqlite3`에 저장됩니다. `--db 다른경로.sqlite3`로 분리할 수 있습니다.

## 정적 시연판 (백엔드 없이, 오프라인)

심사위원용으로 프런트엔드만으로 처음부터 끝까지 동작하는 빌드입니다. 재현 실행, 경기 상세와 판정 근거, 재편성, 사유 입력과 승인, 모의 알림, 운영 기록 내려받기, 참가팀 일정, 8월 8일 장면 전환이 모두 됩니다. PDF와 CSV는 미리 만든 시연용 기록이며 화면에 "사전 생성된 시연용 기록"이라고 적혀 있습니다.

```powershell
Push-Location frontend
npm run build:demo
node scripts/serve-static.mjs dist-demo 8128 /heattime/
Pop-Location
```

http://127.0.0.1:8128/heattime/ 을 엽니다. 해시 라우팅과 상대 경로만 쓰므로 GitHub Pages 같은 하위 경로에서도 열립니다. 다른 기준 경로가 필요하면 `VITE_BASE` 환경 변수로 바꿉니다. "시연 자료 저장됨"이 보이면 인터넷을 끊어도 새로고침과 전체 흐름이 됩니다. 배포된 시연판: https://coomind.github.io/heattime/ (2026-10-21, 작성자 승인 후 GitHub Pages에 배포). 배포 절차는 [docs/deploy-github-pages.md](docs/deploy-github-pages.md)에 있습니다.

## 테스트

```powershell
.\.venv\Scripts\python.exe scripts/prepare_regression_evidence.py
.\.venv\Scripts\python.exe -m pytest -q
Push-Location frontend
npx playwright install chromium
npm run test:unit
npm run build
npm run test:e2e
npm run build:demo
npm run test:e2e:demo
Pop-Location
```

- `tests/test_display_baseline.py`는 세 관측 장면의 배정과 연기, 단계 분포, 열 노출 점수, 시간대별 판정값과 중앙 추정과 범위를 고정값과 비교합니다. 고정값은 `scripts/freeze_display_baseline.py`가 스냅샷과 새 재현이 일치할 때만 씁니다.
- `npm run test:e2e`는 서버 모드를 데스크톱과 휴대폰 크기로 검사합니다(포트 8127, 실행마다 새 SQLite). `npm run test:e2e:demo`는 정적 시연판을 하위 경로에서 띄우고 외부 요청을 모두 막은 채 전체 흐름과 오프라인 새로고침을 검사합니다(포트 8128).
- 접근성(axe, serious와 critical 0건)과 색 대비(WCAG AA 4.5:1)도 자동 검사합니다.
- 솔버의 OPTIMAL과 FEASIBLE 표시는 CPU와 부하에 따라 달라질 수 있습니다. 기록된 시간은 Windows 개발 PC 기준입니다.

## 관측 자료로 분석과 스냅샷 다시 만들기 (네트워크 불필요)

커밋된 `data/observations/`의 정규화 관측 파일만 읽습니다. API 호출과 키 로드는 없습니다.

```powershell
.\.venv\Scripts\python.exe scripts/replay_asos_dates.py            # 62일 재현
.\.venv\Scripts\python.exe scripts/build_observed_snapshot.py      # 세 관측 장면 스냅샷
.\.venv\Scripts\python.exe scripts/build_demo_snapshot.py          # 합성 날씨 장면
.\.venv\Scripts\python.exe scripts/build_snapshot_evidence.py
.\.venv\Scripts\python.exe scripts/build_plan_review_assets.py
.\.venv\Scripts\python.exe scripts/freeze_display_baseline.py      # 판정 기준을 바꾼 경우에만
.\.venv\Scripts\python.exe scripts/export_demo_numbers.py          # 발표용 수치 파일
.\.venv\Scripts\python.exe scripts/build_font_subset.py            # 앱 문구를 바꾼 경우
```

전체 재생성 순서(방식 비교, 민감도, 16팀 규모 분석 포함)는 [재계산 기록](docs/recalc-2026-10-21.md)에 있습니다.

## 활용 영상 다시 만들기

녹화용 래퍼와 스크립트는 `scripts/demo-video/`에만 있고 앱 빌드에는 들어가지 않습니다. 정적 시연판을 1440×702로 띄워 4/3배로 키운 화면을 2배 해상도(3840×2160)로 녹화한 뒤 1920×1080으로 줄입니다. 장면은 화면 맨 위 또는 카드 하나만 잡고, 자막은 아래 144px 띠에만 씁니다. 도입과 마무리 클립과 배경음은 `incoming/video_kit*/`에서 읽습니다.

```powershell
.\.venv\Scripts\python.exe scripts/export_demo_numbers.py
Push-Location frontend
npm run build:demo
Pop-Location
.\.venv\Scripts\python.exe scripts/demo-video/render_pdf_page.py
node scripts/demo-video/record.mjs
.\.venv\Scripts\python.exe scripts/demo-video/compose.py
.\.venv\Scripts\python.exe scripts/package_submission.py
```

## 실제 ASOS 자료 수집 (사용자가 직접 실행)

수집 스크립트 `scripts/fetch_asos_samples.py`는 사용자가 직접 실행합니다. 프로젝트 루트 `.env`의 `KMA_API_KEY`(공공데이터포털 Decoding 키)를 읽으며, 키와 요청 주소를 화면이나 파일에 남기지 않습니다. 근거 문서와 절차는 [ASOS 요약](docs/kma/asos-spec.md)과 [수집 준비 보고](docs/kma/asos-fetch-report.md)에 있습니다.

```powershell
.\.venv\Scripts\python.exe scripts/fetch_asos_samples.py --check
```

## 검증한 것과 하지 않은 것

| 항목 | 상태 |
|---|---|
| 기상청 관측 62일로 같은 가상 대회를 날마다 재현 | 했음. 새 기준에서 930경기 중 699경기 배정, 231경기 연기. 전부 배정 28일, 일부 배정 32일, 0경기 배정 2일(8/4, 8/6) |
| 재편성 일정의 하드 제약(구장 정리, 팀 휴식, 선행 경기, 운영 시간, 일몰) 검사 | 했음 |
| 일사 추정과 관측 비교 | 했음. 927시간, MAE 62.67W/m² |
| 정적 시연판의 오프라인 전체 흐름 | 했음(브라우저 자동 시험) |
| 현장 WBGT 측정값과 대조 | 하지 않음 |
| 국내 구장 보정값(+2.5℃) 검증 | 하지 않음 |
| 대회 운영자 인터뷰 | 하지 않음 |
| 실시간 예보 연동 | 하지 않음(관측 재현과 최신 관측 1회 확인만) |
| 외부 배포 | 정적 시연판만 GitHub Pages에 배포함(https://coomind.github.io/heattime/). 서버 기능은 배포하지 않음 |

## 데이터 출처와 한계

- 기상 자료: 기상청. 관측소 1곳의 자료를 가상 구장 3곳에 함께 쓰므로 구장 사이의 차이는 반영하지 않습니다.
- 일사 `icsr`는 보고 시각 이전 1시간 에너지(MJ/m²)를 시간평균 W/m²로 바꿔 쓰고, 결측은 같은 구간의 모델 추정으로 채웁니다.
- 표면 유형(인조잔디 등)은 판정에 반영하지 않습니다(보정 0℃). 인조잔디는 표면온도 주의 표시만 합니다.
- 열 노출 비교는 공통 경기만 비교하고 연기 수는 따로 보고합니다. 10초 안에 최적을 증명하지 못한 결과는 최소 연기 증명이 아닐 수 있습니다.
- 모든 가상 구장, 팀, 연락처에는 "가상 예시" 라벨을 붙였고 실제 개인정보를 만들지 않았습니다.
- `.env`는 Git에서 제외되며 `.env.example`에는 빈 `KMA_API_KEY` 자리만 있습니다.

## 라이선스와 근거

- WBGT 계산은 Liljegren(2008) 모델의 공개 구현 lwbgt 1.0.1을 씁니다. Apache-2.0과 Argonne WBGT 1.1 원문, NOTICE는 [docs/licenses](docs/licenses)에 있습니다. "This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the Department of Energy."
- 화면 서체는 IBM Plex Sans KR(KS X 1001 한글 2,350자, 영문, 숫자, 앱 문구만 남긴 서브셋)과 IBM Plex Mono이며, PDF 서체는 NanumGothic입니다. 모두 SIL Open Font License 1.1입니다.
- 의존성 라이선스 목록과 기상 자료 출처 표기는 `scripts/package_submission.py`가 `submission/licenses/`에 만듭니다.
- [기술 선택과 출처](docs/engine-sources.md), [제출 준비 보고](docs/submission-report.md), [재계산 기록](docs/recalc-2026-10-21.md).
