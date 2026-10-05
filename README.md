# 히트타임 (HeatTime)

생활체육·유소년 축구대회 운영을 위한 폭염 의사결정 보조 웹 서비스.
기준 명세는 [docs/spec.md](docs/spec.md), 작업 규칙은 [AGENTS.md](AGENTS.md)입니다.
수원 지역 가상 구장 3곳·유소년 12팀·15경기를 API 키 없이 시연합니다.
기본 모드는 합성 예시이며, **기상청 관측 자료**를 선택하면 수원119의2026년7~8월 시간자료로 재현합니다.
대회·팀·구장은 가상 예시이며 WBGT는 현장 실측이 아닌 추정값입니다.

공모전 준비: [공식 요강과 프로젝트 비교](docs/submission/competition-fit.md), [소개·제안서 원고](docs/submission/proposal.md), [운영자 검증 계획](docs/submission/validation-plan.md), [제출 확인 목록](docs/submission/submission-checklist.md).
[심사 자료 한 장 요약](docs/competition-evidence/judge-brief.md)에서 실제 화면·같은 제약 비교·미검증 사항을 함께 확인할 수 있습니다.
현장 도입·고객·가격은 미검증이며 발표 파일·영상·외부 배포는 아직 준비 완료가 아닙니다.

## 설치 및 실행 (Windows PowerShell)

새 Windows 복제본 검증 환경은 Python 3.13.9와 Node.js 24.19.0입니다. 프로젝트 폴더에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Push-Location frontend
npm ci
npm run build
Pop-Location
.\.venv\Scripts\python.exe -m backend.run --host 127.0.0.1 --port 8000
```

[로컬 시연 열기](http://127.0.0.1:8000). 기본 합성/저장 관측/스냅샷 시연에는 키나 .env 생성이 필요 없습니다.
Vite도 envDir:false로 설정하여 .env를 읽지 않습니다.
개발 중에는 별도 창에서 frontend의 `npm run dev`를 실행해 화면을 수정할 수 있습니다.
SQLite는 data/heattime.sqlite3에 저장됩니다. `--db 다른경로.sqlite3`로 분리할 수 있습니다.

## 혼자 따라 하는 시연

1. 재현 모드의 **기상 자료 → 기상청 관측 자료 · 수원119**를 선택. 추천일2026-07-10·가상 대회를 확인하고 **재현 시뮬레이션 실행 →**.
2. 대시보드에서 구장×시간 단계(색·아이콘·텍스트)와 추정값·범위를 확인.
3. 경기 행을 눌러 시간별 WBGT 추정 범위, 정책 출처, 입력 기상·가정을 확인.
4. 재편성 비교 → 재편성 실행. **자동 제안 요약**에서 배정·연기 수, 원래 중지 단계 경기의 제안 배정 수, 공통 경기 점수 변화를 확인. 승인 전 제안임을 확인하고 연기 사유를 읽습니다.
   **경기별 자동 제안 변경 내역**에서는 원래/제안 킥오프·구장·권고 반영 종료·연기 사유를 확인합니다. 경기 버튼은 원래 경기의 상세를 엽니다. **자동 제안 근거**와 승인 후 **승인 일정 근거**는 해당 일정의 WBGT·범위·팀 휴식·선행·정리·일몰 제약을 별도로 보여줍니다.
5. 판단 사유를 적고 제안 승인. 직접 수정은 동일 경기 집합을 유지하고 제약을 다시 검사합니다.
6. 알림 로그에서 팀별 **가상 예시·모의 발송**과 연기 사유를 확인. 실제 문자/카카오는 발송하지 않습니다.
7. 운영 기록에서 PDF·CSV·전체 근거 JSON 다운로드. 읽기 전용 팀 일정 링크도 열어봅니다.

설정 화면은 구장·대회·팀·대진 등록/수정/삭제, CSV 가져오기, 수동 WBGT 입력을 지원합니다.
**CSV 저장 전 미리보기**에서 선택 대회의 양식을 내려받고 파일을 고릅니다. 파일 선택은 저장하지 않습니다. 신규/수정/동일 경기와 행별 오류를 확인하고 **확인한 CSV 저장**을 누릅니다. 확인 뒤 자료가 변경되면 **CSV 다시 확인**이 필요합니다.
CSV 예시는 [data/mock/matches.csv](data/mock/matches.csv). 시간은 +09:00을 포함하고 선행 ID는 세미콜론으로 구분합니다.
히트맵 시간 셀의 **입력 근거**에서 관측 단위·일사 변환·결측·가정·보정 이력을 확인할 수 있습니다. 제안/승인 일정에도 같은 근거 버튼이 있습니다.
설정 변경과 실측 입력은 새 재현 실행부터 반영됩니다. 실제 실측과 합성 입력은 혼합 보정하지 않습니다.

## 실제 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_presentation.py
.\.venv\Scripts\python.exe scripts/check_submission.py
.\.venv\Scripts\python.exe scripts/check_competition_evidence.py
.\.venv\Scripts\python.exe -m backend.engine.validate_solar
Push-Location frontend
npx playwright install chromium
npm run test:unit
npm run build
npm run test:e2e
Pop-Location
```

Playwright는 데스크톱과 휴대폰 크기로 재현→승인→알림→PDF→읽기 전용 흐름을 실행합니다.
테스트는 별도 포트8127과 실행마다 새 SQLite를 사용하고 기존 서버를 재사용하지 않습니다. 포트8127이 사용 중이면 먼저 충돌을 해결하세요.
테스트 출력·이미지·PDF는 data/output/ 아래에 저장되며 git에서 제외됩니다.
`npm run test:unit`는 제안 요약·경기별 변경·전체기간 증거의 관측 수치·공통 경기·연기 별도·점수 증가·0분모·원본 지문을 검사하고 두 스냅샷의 일정 상세·입력 근거 지문을 검사합니다(21개).
`npm run test:e2e:repeat`는 먼저 빌드하고 데스크톱/모바일의 합성/관측 일반·오프라인 흐름, 스냅샷 버전 교체, 승인 전/후 결과 요약, 전체기간 증거·경기 변경·입력 근거·CSV·최신 관측 표시를 각각3번 실행합니다(총84개). 최신 관측 API 화면 검사는 가짜 응답을 주입하므로 실제 키를 읽거나 기상청에 호출하지 않습니다.

재현 모드의 **62일 전체 재현 결과와 알고리즘 비교**를 펼치면 유리한 날짜만 추리지 않은 전체 결과를 확인할 수 있습니다. 기본값의 별도 가상 대회 분석이며 현재 선택한 대회·설정을 다시 계산한 결과가 아닙니다. 같은 제약의 탐욕 비교는 그 안의 별도 표입니다. 배정 합계506→562건과 공통 점수1.39% 증가를 함께 표시하며 사람의 업무 효과나 건강 효과로 해석하지 않습니다.

[알고리즘 비교 재현 절차](docs/competition-evidence/reproduce.md)를 확인하세요. 분석을 재실행한 뒤 화면 증거만 갱신할 때는 `./.venv/Scripts/python.exe scripts/build_period_evidence.py`와 프론트엔드 빌드를 실행합니다. 기존 관측 스냅샷·62일 순위·정책을 바꾸지 않습니다.

## 연결 없는 시연 스냅샷

재현 모드에서 **관측 시연 스냅샷 열기 →** 또는 [관측 스냅샷](http://127.0.0.1:8000/#snapshot-observed)을 엽니다.
관측 스냅샷은 **수원119·2026-07-10·15배정/0연기·공통 점수6114→4319**의 고정된 결과입니다.
기존 합성 스냅샷은 **합성 시연 스냅샷 열기 →** 또는 [합성 스냅샷](http://127.0.0.1:8000/#snapshot)에서 별도로 보존했습니다.
**시연 자료 저장됨 · 연결 없이 새로고침 가능**이 표시되면 연결을 끊어도 새로고침과 전체 흐름을 진행할 수 있습니다.
브라우저를 완전히 새로 설치한 상태의 첫 방문은 정적 파일을 읽을 로컬 서버가 필요합니다.
캐시를 지우면 처음 한 번 다시 저장해야 하며, 개발 서버 대신 `npm run build` 결과에서 사용합니다.
새 빌드는 캐시 버전도 바뀝니다. 연결된 상태에서 스냅샷을 열고 저장 완료를 기다린 뒤 한 번 새로고침하여 새 버전을 불러오세요.

**스냅샷 재현 실행 →** → 히트맵 → 경기 상세 → 재편성 실행 → 제안 승인 → 모의 알림 → PDF 순서입니다.
관측/합성 모드별로 사전 계산된 기상 입력·추정 위험도·제안·승인 예시·모의 로그·PDF/CSV/JSON을 사용합니다.
스냅샷 동안 기상 API·서버 API·솔버를 호출하지 않습니다. 날짜·운영값·판단 사유는 고정 예시입니다.
사전 계산 승인만 시연하며 수정/거절·등록·실측 저장은 일반 재현에서 사용합니다.
화면과 PDF에 **시연 스냅샷**과 **실제 운영 판단 기록 아님**을 표시합니다.
기본 mock 프로필의 연기가 많아도 결과를 바꾸지 않았고, 실제 관측 시연 후보로 제시하지 않습니다.
브라우저 메모리의 승인 시연 상태는 새로 재현하거나 페이지를 새로고침하면 초기화됩니다.
정적 서비스 워커는 API/개인정보를 캐시하지 않고 같은 주소의 화면 자산만 저장합니다.

사전 계산 자료를 다시 만들 때는 개발자가 `python scripts/build_demo_snapshot.py` 후 `npm run build`를 실행합니다.
이는 로컬 합성 계산이며 **ASOS 수집 스크립트가 아닙니다**. 관측 스냅샷은 아래 재현 결과를 사용합니다. 정책·기본 운영값은 그대로입니다.

## 실제 관측의 분석·스냅샷 재생성 (네트워크 불필요)

커밋된 `data/observations/`에는 인증 정보가 없는 관측 필드만 담겨 있어 새 복제본에서도 재현됩니다.
원본 `data/samples/`는 Git에서 제외됩니다. 원본 해시와 시간·단위 근거는 [관측 근거](docs/kma/asos-observation-evidence.md)에 있습니다.

```powershell
# 기존 관측 파일로 비교와62일 일정 분석. API 수집·키 로드 없음.
.\.venv\Scripts\python.exe -m backend.engine.validate_solar --observed
.\.venv\Scripts\python.exe scripts/replay_asos_dates.py
# 위 분석에서 추천1순위의 기존 제안을 고정. 다시 솔버를 돌리지 않음.
.\.venv\Scripts\python.exe scripts/build_observed_snapshot.py
Push-Location frontend
npm run build
Pop-Location
```

새 원본을 정규화할 때만 `prepare_asos_observations.py 원본.json`을 사용합니다. 수집기는 실행하지 않습니다.
다른 지점/기간 파일은 실제 자료와 문서 확인 후 분석·스냅샷·발표 문서를 함께 갱신해야 합니다.
현재 어댑터는 확인한 필드·단위와24시간 완전한 날짜만 사용하며 누락을 합성으로 대체하지 않습니다.

일사 `icsr`는 이전1시간 에너지MJ/m² → 시간평균W/m²입니다. 927시간 비교에서MAE62.67W/m²·편향+6.74W/m², 561시간 결측 제외.
정시 운량/강우를 한 시간 동안 일정하게 두는 한계, 시간평균을 정시 WBGT 입력의 대표값으로 사용하는 한계를 기록합니다.
실제 관측소1곳을 가상3구장에 공유하므로 구장 기상이나 현장 WBGT 오차 검증으로 해석하지 않습니다.
전체 결과와 직접 확인 목록은 [실제 자료 보고](docs/real-data-report.md)에 있습니다.

## 실제 ASOS 샘플 수집 준비 (사용자가 직접 실행)

근거는 docs/kma/에 제공한 DOCX 한 문서뿐입니다. [요약](docs/kma/asos-spec.md),
[수집 준비 보고](docs/kma/asos-fetch-report.md)를 확인하세요.
에이전트는 실제 수집 명령을 실행하지 않았고 프로젝트 .env를 직접 열거나 출력하지 않았습니다.
수집 결과는 자동 반영하지 않습니다. 검증된 정규화 파일을 관측 모드에서 사용하며 현장 WBGT 검증은 별도입니다.

프로젝트 루트의 .env에서 **KMA_API_KEY에 공공데이터포털 Decoding 키**를 설정하세요.
URL Encoding 키를 넣지 않습니다. 스크립트가 요청을 만들 때 한 번 인코딩합니다.
키를 명령행 인자로 넘기거나 화면에 출력하지 마세요.
`.env`는 현재 작업 폴더와 관계없이 **수집 스크립트 위치 기준의 프로젝트 루트**에서 찾습니다.
실행 시 키 길이와 `%` 문자 포함 여부만 알려줍니다. `%` 포함은 포털의 Decoding 키와 다시 대조할 단서이며, 스크립트가 키를 임의로 디코딩해서 바꾸지는 않습니다.

PowerShell에서 아래를 **본인이** 실행합니다. 프로젝트 가상환경의 Python과 스크립트를 절대 경로로 지정하므로 다른 작업 폴더에서도 사용할 수 있습니다.

먼저 연결만 점검하려면:

```powershell
$heatTimeRoot = 'C:\Users\coomi\OneDrive\바탕 화면\Heattime'
& (Join-Path $heatTimeRoot '.venv\Scripts\python.exe') (Join-Path $heatTimeRoot 'scripts\fetch_asos_samples.py') --check
```

`--check`는 **119 수원·2026-07-01 하루·첫 페이지 10건**만 요청합니다. 페이지를 추가로 받거나 일사 보조 지점을 호출하거나 파일을 저장하지 않습니다. 24시간 전체 수집 성공을 확인하는 모드는 아닙니다.
점검 날짜는 `--start`로 바꿉니다. 점검 중 `--station`, `--end`, `--page-size`, `--solar-station`은 사용하지 않고 수원·하루·기본10건으로 고정합니다.

```powershell
& (Join-Path $heatTimeRoot '.venv\Scripts\python.exe') (Join-Path $heatTimeRoot 'scripts\fetch_asos_samples.py') --check --start 2026-07-02
```

실패 시 **실패 단계(키 로드 / 네트워크 연결 / HTTP 응답 / 응답 파싱), HTTP 상태 코드, 본문의 resultCode·resultMsg, 예외 클래스 이름**만 진단으로 출력합니다. XML 오류 문서이면 그 문서에 실제 존재하는 코드·메시지 요소를 골라 표시합니다. 값이 없거나 HTTP 응답을 받지 못했으면 `없음`으로 표시합니다. 키가 없거나 비었으면 별도로 **키를 찾지 못함**을 알려줍니다.

응답 코드·메시지 안의 키(인코딩된 형태 포함), URL, 요청 헤더는 마스킹합니다. 전체 본문·예외 원문·요청 헤더는 출력하지 않으며 진단 파일도 만들지 않습니다. XML 오류의 범용 진단은 실제 ASOS 관측 필드 어댑터를 확정하는 작업과 별개입니다.
[진단 변경·테스트 보고](docs/kma/asos-diagnostics-report.md)를 참고하세요.

기간 전체 수집은 점검 옵션 없이 실행합니다:

```powershell
& (Join-Path $heatTimeRoot '.venv\Scripts\python.exe') (Join-Path $heatTimeRoot 'scripts\fetch_asos_samples.py')
```

기본값은 가이드 지점 표의 **119 수원**, **2026-07-01 00시~2026-08-31 23시**입니다.
페이지마다 기본10건(가이드 기본값), 호출 사이0.2초 대기, 마지막 페이지까지 받아 합칩니다.
지점·기간은 아래처럼 변경합니다.108 서울은 가이드에 있는 지점이며 일사 관측/거리 예시는 아닙니다.

```powershell
& (Join-Path $heatTimeRoot '.venv\Scripts\python.exe') (Join-Path $heatTimeRoot 'scripts\fetch_asos_samples.py') --station 108 --start 2026-07-01 --end 2026-07-31
```

결과는 `data/samples/asos_119_20260701_20260831.json` 같은 지점·기간별 파일입니다.
인증키·요청 URL·요청 헤더·전체 응답/예외 원문은 저장/출력하지 않습니다. 진단의 코드·메시지만 민감값을 마스킹해서 표시합니다. 기존 같은 이름 파일을 덮어쓰지 않습니다.
페이지 중복·총건수 변경·진행 중단은 성공으로 처리하지 않습니다.
한 달/두 달 조회가 실제 서비스에서 제한되면 원문에는 최대 기간이 없으므로 제한 값을 추측하지 않습니다.
위 기간 인자를 줄여 별도 수집한 뒤 오류/응답의 키를 제거한 자료로 후속 확인합니다.
`--page-size`는 조절할 수 있지만 최대 허용값은 문서에 없습니다. 기본값을 먼저 사용하세요.

매 날짜마다 최고기온·최저습도·일사값 존재 여부와 결측 시간을 출력하고 JSON에도 넣습니다.
기온/습도 품질 플래그1(오류)·9(결측)는 요약에서 제외합니다. 원문은 정상null, 표 샘플0으로 서로 달라
그 외 플래그의 의미를 확정하지 않습니다. 수치형 결측 센티널은 추측하지 않습니다.
일사 결측 집계는 빈/누락/비수치·미수신 시간을 포함하며 **0.0은 존재하는 일사값**입니다.
수집기는 원본icsr 단위MJ/m2를 보존하며 변환하지 않습니다. 관측 어댑터의 시간평균 변환 근거는 별도 문서에 있습니다.

### 수원 일사값이 전부 비었을 때

가이드 지점 표는 번호·이름·관리관서만 제공하며 **일사 관측 여부·좌표·거리 정보가 없습니다**.
따라서 “일사를 관측하는 가까운 지점”의 자동 지정은 **TODO**입니다.
본인이 별도로 확인한 지점이 가이드 표에 있을 때 아래처럼 지정할 수 있습니다.
수원icsr 값이 기간 전체에서 비어 있으면 추가 지점을 같은 기간에 받아 별도 파일로 저장합니다.

```powershell
# 아래 값은 본인이 일사 관측 여부와 가까운 위치를 확인한 가이드 표 지점번호로 바꾸세요.
# 문자열이 아니라 실제 번호로 바꾼 뒤 실행합니다.
& (Join-Path $heatTimeRoot '.venv\Scripts\python.exe') (Join-Path $heatTimeRoot 'scripts\fetch_asos_samples.py') --solar-station '<확인한_지점번호>'
```

임의 지점을 일사 관측소로 추천하지 않습니다. 추가 지점도 실제 응답에 일사값이 있는지는 날짜별 요약으로 확인하세요.
가이드는 HTTP 요청 주소를 제공하며 HTTPS 지원은 명시하지 않습니다. 수집기는 원문HTTP 주소를 그대로 사용합니다.
실제 API 연결 성공·기간 전체 수신·일사 관측 여부는 본인 실행 후 확인해야 합니다.

## 배포

[docs/deployment.md](docs/deployment.md), Dockerfile, render.yaml을 준비했습니다.
사용자 지시에 따라 실제 배포·로그인을 하지 않았습니다. 외부 서비스 링크는 아직 없습니다.
무료 호스팅의 임시 저장소에서 기록이 사라질 수 있으므로 제출 전 내보내기와 외부 전체 흐름을 확인하세요.

## 데이터 출처와 한계

- 가상 구장·팀·연락처와 합성 기상에 가상 예시 라벨. 실제 관측은 확인된119수원·날짜로 표시하며 개인정보를 만들지 않습니다.
- mock ASOS 일사도 합성 값입니다. 그래프·오차 지표는 파이프라인 시연이며 실제 정확도 근거가 아닙니다.
- 실제 ASOS 샘플 어댑터는 연결 완료. 실시간 예보 API는 어댑터+TODO 상태이며 확인되지 않은 필드는 추측하지 않습니다.
- 내부 source는 공급자 계열, is_mock은 진위 구분. KST와 수집 시각을 보존합니다.
- WBGT는 Liljegren 공개 lwbgt1.0.1 구현. 태양·맑은하늘은 pvlib. 현장 보정과 범위, 간이 폴백 상태를 기록합니다.
- 기압1013.25hPa·고도0m·풍속10m 입력 등 가정을 기록하며 현장 검토가 필요합니다.
- 정책 출처·원문 대조 필요 표시: backend/config/policies.yaml. 연령 보정은 전문가 자문이 필요한 설계 가정입니다.
- 열 노출 비교는 공통 경기만, 연기 수는 별도. 시간 제한 내 FEASIBLE/탐욕 결과는 최소 연기 증명이 아닐 수 있습니다.
- 에이전트는 프로젝트 .env를 읽거나 출력하지 않습니다. 관측/합성 재현·스냅샷·서버 시작은 키를 읽지 않습니다. 사용자 직접 실행 ASOS 수집기와 아래 최신 관측 API 갱신만 실행 시 서버에서 해당 키를 읽습니다.
- 의사결정 보조이며 최종 운영 판단은 주최자입니다. 영상 기반 개인 부하는 구현 범위 밖 연구 단계입니다.
- 현재 공개 데모용 공유 입력이며 실제 운영용 계정·권한·개인정보 처리는 별도 설계가 필요합니다.

## 라이선스·근거

lwbgt 공개 구현의 Apache-2.0 및 Argonne WBGT1.1 원문·NOTICE는 [docs/licenses](docs/licenses)에 보존합니다.
“This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the Department of Energy.”
한글 PDF는 NanumGothic 글꼴을 포함하고 SIL Open Font License 원문을 backend/assets/fonts/OFL.txt에 보존합니다.
[기술 선택·출처](docs/engine-sources.md), [최종 보고](docs/final-report.md), [발표 자료](docs/presentation/slides.md)를 참조하세요.


## 최신 기상청 관측 연결

실시간 **기상 관측 입력 기반 WBGT 추정**을 지원합니다. 현장 WBGT 측정기나 미래 예보 연결은 아닙니다. [공식 문서·사용 필드·제약](docs/kma/aws-minute-spec.md).

1. [API허브](https://apihub.kma.go.kr/) 가입·연락처 확인 후 마이페이지의 키를 발급받습니다. [AWS 페이지](https://apihub.kma.go.kr/apiList.do?seqApi=2&seqApiSub=239)의 **1.1 AWS 매분자료** 활용신청을 완료합니다. 로그인/인증은 사용자가 직접 합니다.
2. 프로젝트 루트 .env에 `KMA_APIHUB_KEY=발급받은키`를 직접 추가합니다. 기존 공공데이터포털 KMA_API_KEY와 별개입니다. 키를 채팅/화면에 붙이지 않습니다.
3. 프론트엔드를 다시 빌드하고 프로젝트 가상환경 서버를 다시 시작합니다.

```powershell
Set-Location 'C:\Users\coomi\OneDrive\바탕 화면\Heattime'
Push-Location frontend
npm run build
Pop-Location
.\.venv\Scripts\python.exe -m backend.run --host 127.0.0.1 --port 8000
```

4. [일반 로컬 화면](http://127.0.0.1:8000)의 **재현 모드** 아래 **최신 관측과 WBGT 추정**으로 내려갑니다. 기본 합성 입력은 키 없이 점검됩니다. 실제 연결은 **최신 관측 연결 → 기상청 API허브 · AWS 매분자료**, 수원 **119** 확인, **최신 관측 갱신**을 누릅니다. 서버에서 이때만 키를 읽습니다.
5. 기상청 관측 표시와 **관측 시각/가져온 시각**을 확인합니다. 키 로드 실패는 설정 확인, HTTP 401은 키 확인, HTTP 403은 해당 API 활용신청 확인입니다. 형식 오류·자료 없음은 추측으로 채우지 않습니다. 실패 후 이전 자료가 남아 있으면 관측 시각을 다시 확인합니다.

같은 지점 자료를 등록 구장에 공유하고 앱 전체 60초 호출 간격을 유지합니다. 일 2만 회·5GB 제한과 앱 사용량을 표시하지만 다른 앱의 동일 키 사용량은 합산하지 못합니다. 실패 응답 용량은 최대 1MiB로 보수 집계합니다. 자동 반복 호출은 하지 않으며 시연 스냅샷에서는 버튼을 비활성화합니다.

이 서비스에는 일사·운량·WBGT 필드가 없습니다. 일사는 기존 모델과 운량 0.7 가정으로 추정하고 관측 압력은 참고로만 표시합니다. 기존 스크리닝 기압·높이 가정·구장 보정·판정·범위는 유지합니다. 같은 관측소 1곳의 공간 대표성은 미검증이며 최신 관측이 미래 경기 시각을 대표하지 않습니다. 기존 재현/승인 기록을 변경하지 않습니다. 에이전트는 실제 키 확인·API 호출·수집 스크립트 실행을 하지 않았습니다.
