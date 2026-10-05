# 오프라인 계산 검증 재현

이 절차는 이미 저장된 관측 자료만 읽는다. `.env`나 수집 스크립트는 사용하지 않는다. 기본 엔진·정책·시간 제한은 바꾸지 않는다. 아래 명령은 프로젝트 루트의 PowerShell에서 실행한다.

## 소스 대조 준비

정규 앱 실행에는 C 컴파일러가 필요 없다. 내부 태양 위치·직달/산란 값을 원소스 그대로 추적하는 이 분석에만 Git과 MinGW GCC가 필요하다. 설치된 라이브러리를 덮어쓰지 않는다. 분석 당시 `gcc.exe`는 `C:\mingw64\bin\gcc.exe`였다.

```powershell
git clone --depth 1 --branch v1.0.1 https://github.com/zyf0717/lwbgt.git data/output/wbgt-sanity/lwbgt-source
.\.venv\Scripts\python.exe scripts/wbgt_sanity.py --mode traces
.\.venv\Scripts\python.exe scripts/wbgt_sanity.py --mode sensitivity
.\.venv\Scripts\python.exe -m pytest -q
```

소스가 이미 있으면 다시 clone하지 않는다. 분석 스크립트는 지정한 커밋과 비교하고, 대상 시각의 C 출력이 설치된 라이브러리와 일치하는지 확인한 후 내부 분리값을 기록한다. `--source`로 소스 폴더를 바꿀 수 있다. 원래 실제 샘플이 있으면 해시 대조 후 허용된 기압 필드만 읽고, 새 clone에서 원본이 없으면 커밋된 기압 근거를 사용한다. 기상 입력은 기존 정규화 관측 자료를 사용한다.

기본 모드의62일 재현 일정은 기존 `docs/real-data/replay-results.json`의 최적 배정 근거를 유지하고, 새로 계산한4,464개 WBGT·입력 해시를 기존 상세 기록이 있으면 대조한다. 민감도는9개 변경 가정×62일을 실제로 다시 풀며, 매번 같은10초 제한·15분 슬롯·휴식·대진·일몰·3구장 제약을 지킨다. 상대습도·기온·일사·풍속 원관측은 바꾸지 않는다. 구장별±1℃는 공간 차이를 알 수 없는 상황의 **가상 WBGT 편차**이며 새 관측소 자료나 신뢰구간이 아니다.

출력 위치:

- `docs/wbgt-sanity/peak-traces.json`, `peak-tables.md`: 단위·성분·단일 입력 비교.
- `docs/wbgt-sanity/pressure-evidence.json`: 고정 허용 필드의 관측 기압 근거.
- `docs/wbgt-sanity/sensitivity-results.json`: 분석 가정별 날짜 결과·집계·증명 상태.
- `data/output/wbgt-sanity/`: 분석 DB·새 계산 세션·분석용 DLL·일정 상세. Git에서 제외된다.

스냅샷·PDF·기존62일 결과·발표 원고를 갱신하는 명령은 이 절차에 없다. 명백한 생산 엔진 버그가 확인되지 않았기 때문이다. 표만 다시 렌더링할 때는 `--mode tables`를 사용한다.
