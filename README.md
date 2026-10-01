# 히트타임 (HeatTime)

생활체육·유소년 축구대회 운영을 위한 폭염 의사결정 보조 서비스.
유일한 기준 명세는 [docs/spec.md](docs/spec.md), 작업 규칙은 [AGENTS.md](AGENTS.md)입니다.
현재 P1만 구현했습니다. 화면/API/추정 엔진은 P2 이후 구현합니다.

## 설치 및 실행

Python 3.11 이상. P1 실행에는 Python 표준 라이브러리만 사용합니다.
프로젝트 폴더에서 다음 명령을 실행합니다(PowerShell).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m backend.weather.cli --date 2026-08-01
.\.venv\Scripts\python.exe -m backend.weather.cli --date 2026-08-01 --provider asos
.\.venv\Scripts\python.exe -m pytest -q
```

이미 pytest가 설치된 Python이면 `python -m pytest -q`로 실행할 수 있습니다.
각 수집은 구장 3곳 × 24시간 = 72건을 `data/heattime.sqlite3`에 저장합니다.
같은 날짜와 공급자를 재실행해도 중복되지 않습니다. 예보/관측 자료는 별도 보존합니다.
기본 날짜는 시연용 합성 데이터 날짜이며 실제 무더위 관측일이라는 뜻이 아닙니다.

## 데이터와 한계

- 모든 mock 구장·기상은 **가상 예시**. 가상 지점 ID는 실제 ASOS 지점 번호가 아닙니다.
- mock ASOS 일사량도 합성 값입니다. 실제 관측 검증이나 엔진 정확도 근거로 쓰지 않습니다.
- `source`는 공급자 계열, `is_mock`은 진위 구분입니다. 조회 시 둘을 명시해야 합니다.
- 시간은 KST(+09:00)로 저장합니다. 수집 시각도 보존합니다.
- 수동 WBGT는 실측값입니다. 기온과 혼동하지 않도록 별도 테이블에 저장합니다.
- .env를 생성·읽기·출력하지 않습니다. `.env.example`에 빈 키 자리만 있습니다.
- 실제 API는 명시적 미구현 오류를 반환합니다. 엔드포인트/응답 스키마를 추측하지 않았습니다.
- 공개 격자 함수 출처와 확인 항목: [docs/p1-checklist.md](docs/p1-checklist.md).
- 기술 스택·폴더·P1~P6: [docs/plan.md](docs/plan.md).

실제 응답을 받으면 인증키와 개인정보를 제거해 `data/samples/`에 저장합니다.
실제 API 키는 이후에도 .env로만 관리하며 git에 포함하지 않습니다.
