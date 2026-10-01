# 히트타임 (HeatTime)

생활체육·유소년 축구대회 운영을 위한 폭염 의사결정 보조 웹 서비스.
기준 명세는 [docs/spec.md](docs/spec.md), 작업 규칙은 [AGENTS.md](AGENTS.md)입니다.
수원 지역 가상 구장 3곳·유소년 12팀·15경기를 API 키 없이 시연합니다.
기상은 mock 합성 자료이며 실제 2026년 관측 재현이나 현장 정확도 검증을 완료한 상태는 아닙니다.

## 설치 및 실행 (Windows PowerShell)

Python 3.13과 Node.js 22를 사용한 개발 환경입니다. 프로젝트 폴더에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Push-Location frontend
npm ci
npm run build
Pop-Location
.\.venv\Scripts\python.exe -m backend.run --host 127.0.0.1 --port 8000
```

[로컬 시연 열기](http://127.0.0.1:8000). 키나 .env 생성이 필요 없습니다.
Vite도 envDir:false로 설정하여 .env를 읽지 않습니다.
개발 중에는 별도 창에서 frontend의 `npm run dev`를 실행해 화면을 수정할 수 있습니다.
SQLite는 data/heattime.sqlite3에 저장됩니다. `--db 다른경로.sqlite3`로 분리할 수 있습니다.

## 혼자 따라 하는 시연

1. 재현 모드에서 수원·2026-08-01·가상 대회를 확인하고 **재현 시뮬레이션 실행 →**.
2. 대시보드에서 구장×시간 단계(색·아이콘·텍스트)와 추정값·범위를 확인.
3. 경기 행을 눌러 시간별 WBGT 추정 범위, 정책 출처, 입력 기상·가정을 확인.
4. 재편성 비교 → 재편성 실행. 공통 경기 열 노출과 별도 연기 수·사유를 확인.
5. 판단 사유를 적고 제안 승인. 직접 수정은 동일 경기 집합을 유지하고 제약을 다시 검사합니다.
6. 알림 로그에서 팀별 **가상 예시·모의 발송**과 연기 사유를 확인. 실제 문자/카카오는 발송하지 않습니다.
7. 운영 기록에서 PDF·CSV·전체 근거 JSON 다운로드. 읽기 전용 팀 일정 링크도 열어봅니다.

설정 화면은 구장·대회·팀·대진 등록/수정/삭제, CSV 가져오기, 수동 WBGT 입력을 지원합니다.
CSV 예시는 [data/mock/matches.csv](data/mock/matches.csv). 시간은 +09:00을 포함하고 선행 ID는 세미콜론으로 구분합니다.
설정 변경과 실측 입력은 새 재현 실행부터 반영됩니다. 실제 실측과 합성 입력은 혼합 보정하지 않습니다.

## 실제 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m backend.engine.validate_solar
Push-Location frontend
npx playwright install chromium
npm run build
npm run test:e2e
Pop-Location
```

Playwright는 데스크톱과 휴대폰 크기로 재현→승인→알림→PDF→읽기 전용 흐름을 실행합니다.
기존 서버가 있으면 그 서버를 사용하므로 코드 변경 후 재시작하세요.
테스트 출력·이미지·PDF는 data/output/ 아래에 저장되며 git에서 제외됩니다.

## 실제 ASOS 샘플 수집 준비 (사용자가 직접 실행)

근거는 docs/kma/에 제공한 DOCX 한 문서뿐입니다. [요약](docs/kma/asos-spec.md),
[수집 준비 보고](docs/kma/asos-fetch-report.md)를 확인하세요.
에이전트는 실제 수집 명령을 실행하지 않았고 프로젝트 .env를 직접 열거나 출력하지 않았습니다.
mock 웹 앱은 그대로 유지하며 수집 결과를 자동으로 실측 검증에 반영하지 않습니다.

프로젝트 루트의 .env에서 **KMA_API_KEY에 공공데이터포털 Decoding 키**를 설정하세요.
URL Encoding 키를 넣지 않습니다. 스크립트가 요청을 만들 때 한 번 인코딩합니다.
키를 명령행 인자로 넘기거나 화면에 출력하지 마세요.

PowerShell에서 아래를 **본인이** 실행합니다.

```powershell
Set-Location -LiteralPath 'C:\Users\coomi\OneDrive\바탕 화면\Heattime'
.\.venv\Scripts\python.exe .\scripts\fetch_asos_samples.py
```

기본값은 가이드 지점 표의 **119 수원**, **2026-07-01 00시~2026-08-31 23시**입니다.
페이지마다 기본10건(가이드 기본값), 호출 사이0.2초 대기, 마지막 페이지까지 받아 합칩니다.
지점·기간은 아래처럼 변경합니다.108 서울은 가이드에 있는 지점이며 일사 관측/거리 예시는 아닙니다.

```powershell
.\.venv\Scripts\python.exe .\scripts\fetch_asos_samples.py --station 108 --start 2026-07-01 --end 2026-07-31
```

결과는 `data/samples/asos_119_20260701_20260831.json` 같은 지점·기간별 파일입니다.
인증키·요청 URL·원문 오류는 저장/출력하지 않습니다. 기존 같은 이름 파일을 덮어쓰지 않습니다.
페이지 중복·총건수 변경·진행 중단은 성공으로 처리하지 않습니다.
한 달/두 달 조회가 실제 서비스에서 제한되면 원문에는 최대 기간이 없으므로 제한 값을 추측하지 않습니다.
위 기간 인자를 줄여 별도 수집한 뒤 오류/응답의 키를 제거한 자료로 후속 확인합니다.
`--page-size`는 조절할 수 있지만 최대 허용값은 문서에 없습니다. 기본값을 먼저 사용하세요.

매 날짜마다 최고기온·최저습도·일사값 존재 여부와 결측 시간을 출력하고 JSON에도 넣습니다.
기온/습도 품질 플래그1(오류)·9(결측)는 요약에서 제외합니다. 원문은 정상null, 표 샘플0으로 서로 달라
그 외 플래그의 의미를 확정하지 않습니다. 수치형 결측 센티널은 추측하지 않습니다.
일사 결측 집계는 빈/누락/비수치·미수신 시간을 포함하며 **0.0은 존재하는 일사값**입니다.
원본icsr 단위MJ/m2를 보존하고 시간 누적 구간이나W/m² 변환을 가정하지 않습니다.

### 수원 일사값이 전부 비었을 때

가이드 지점 표는 번호·이름·관리관서만 제공하며 **일사 관측 여부·좌표·거리 정보가 없습니다**.
따라서 “일사를 관측하는 가까운 지점”의 자동 지정은 **TODO**입니다.
본인이 별도로 확인한 지점이 가이드 표에 있을 때 아래처럼 지정할 수 있습니다.
수원icsr 값이 기간 전체에서 비어 있으면 추가 지점을 같은 기간에 받아 별도 파일로 저장합니다.

```powershell
# 아래 값은 본인이 일사 관측 여부와 가까운 위치를 확인한 가이드 표 지점번호로 바꾸세요.
# 문자열이 아니라 실제 번호로 바꾼 뒤 실행합니다.
.\.venv\Scripts\python.exe .\scripts\fetch_asos_samples.py --solar-station '<확인한_지점번호>'
```

임의 지점을 일사 관측소로 추천하지 않습니다. 추가 지점도 실제 응답에 일사값이 있는지는 날짜별 요약으로 확인하세요.
가이드는 HTTP 요청 주소를 제공하며 HTTPS 지원은 명시하지 않습니다. 수집기는 원문HTTP 주소를 그대로 사용합니다.
실제 API 연결 성공·기간 전체 수신·일사 관측 여부는 본인 실행 후 확인해야 합니다.

## 배포

[docs/deployment.md](docs/deployment.md), Dockerfile, render.yaml을 준비했습니다.
사용자 지시에 따라 실제 배포·로그인을 하지 않았습니다. 외부 서비스 링크는 아직 없습니다.
무료 호스팅의 임시 저장소에서 기록이 사라질 수 있으므로 제출 전 내보내기와 외부 전체 흐름을 확인하세요.

## 데이터 출처와 한계

- 모든 가상 구장·팀·연락처·기상에는 가상 예시 라벨. 실제 지점 번호·개인정보를 만들지 않습니다.
- mock ASOS 일사도 합성 값입니다. 그래프·오차 지표는 파이프라인 시연이며 실제 정확도 근거가 아닙니다.
- 실제 기상 API는 어댑터+TODO 상태. 인증키를 제거한 응답을 data/samples/에 넣고 공식 명세를 제공하면 맞춥니다.
- 내부 source는 공급자 계열, is_mock은 진위 구분. KST와 수집 시각을 보존합니다.
- WBGT는 Liljegren 공개 lwbgt1.0.1 구현. 태양·맑은하늘은 pvlib. 현장 보정과 범위, 간이 폴백 상태를 기록합니다.
- 기압1013.25hPa·고도0m·풍속10m 입력 등 가정을 기록하며 현장 검토가 필요합니다.
- 정책 출처·원문 대조 필요 표시: backend/config/policies.yaml. 연령 보정은 전문가 자문이 필요한 설계 가정입니다.
- 열 노출 비교는 공통 경기만, 연기 수는 별도. 시간 제한 내 FEASIBLE/탐욕 결과는 최소 연기 증명이 아닐 수 있습니다.
- 에이전트와 mock 앱은 .env를 읽거나 출력하지 않습니다. 사용자 직접 실행 ASOS 수집기만 실행 시 키를 읽습니다.
- 의사결정 보조이며 최종 운영 판단은 주최자입니다. 영상 기반 개인 부하는 구현 범위 밖 연구 단계입니다.
- 현재 공개 데모용 공유 입력이며 실제 운영용 계정·권한·개인정보 처리는 별도 설계가 필요합니다.

## 라이선스·근거

lwbgt 공개 구현의 Apache-2.0 및 Argonne WBGT1.1 원문·NOTICE는 [docs/licenses](docs/licenses)에 보존합니다.
“This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the Department of Energy.”
한글 PDF는 NanumGothic 글꼴을 포함하고 SIL Open Font License 원문을 backend/assets/fonts/OFL.txt에 보존합니다.
[기술 선택·출처](docs/engine-sources.md), [최종 보고](docs/final-report.md), [발표 자료](docs/presentation/slides.md)를 참조하세요.
