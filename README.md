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
- .env를 읽거나 출력하지 않습니다. .env.example에는 빈 KMA_API_KEY 자리만 둡니다.
- 의사결정 보조이며 최종 운영 판단은 주최자입니다. 영상 기반 개인 부하는 구현 범위 밖 연구 단계입니다.
- 현재 공개 데모용 공유 입력이며 실제 운영용 계정·권한·개인정보 처리는 별도 설계가 필요합니다.

## 라이선스·근거

lwbgt 공개 구현의 Apache-2.0 및 Argonne WBGT1.1 원문·NOTICE는 [docs/licenses](docs/licenses)에 보존합니다.
“This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the Department of Energy.”
한글 PDF는 NanumGothic 글꼴을 포함하고 SIL Open Font License 원문을 backend/assets/fonts/OFL.txt에 보존합니다.
[기술 선택·출처](docs/engine-sources.md), [최종 보고](docs/final-report.md), [발표 자료](docs/presentation/slides.md)를 참조하세요.
