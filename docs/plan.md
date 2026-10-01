# 구현 계획

사용자가 지정한 docs/spec.md가 유일한 기준 명세다. 아래는 그 명세의 구현 순서다.

## 기술 스택

- Python 3.11+ / FastAPI / SQLite, 시연 우선
- React + Vite + TypeScript / Recharts, 모바일 대응
- pvlib(일사량), OR-Tools CP-SAT(재편성), pytest
- WBGT 공개 구현은 P2에서 라이선스·설치 가능성 확인 후 선택
- PDF 생성 도구와 호스팅은 P5에서 한국어 출력·무료 제공 조건 검증 후 확정
- P1은 의존성을 줄여 표준 라이브러리만 사용. 이후 필요한 단계에서 패키지 추가

## 폴더

```text
AGENTS.md                  작업 규칙
.env.example               빈 키 자리 (.env 읽기 금지)
backend/
  weather/                 P1 데이터 모델·어댑터·격자·저장·실행 도구
  engine/                  P2 예정
  schedule/                P3 예정
frontend/                  P4 예정
tests/                     단계별 검증
data/
  mock/                    가상 예시 구장
  samples/                 사용자가 제공할 실제 응답 (git 제외)
  heattime.sqlite3         실행 결과 (git 제외)
docs/
  spec.md                  원본 명세 그대로 보관
  references/              격자 공식 출처
  plan.md                  단계 계획
  p1-checklist.md           연결 전 확인 항목
  p1-report.md              실행 결과
```

## 단계

| 단계 | 구현 | 수용 기준 |
|---|---|---|
| P1 | 기상 어댑터·격자 양방향 변환·SQLite·수동 WBGT·mock | 3곳 × 24시간 저장 및 테스트 통과 |
| P2 | 일사·WBGT·범위·정책·일사량 비교 | RiskEstimate, 비교 그래프, 오차 지표 |
| P3 | 경기 권고·CP-SAT·폴백·가상 12팀 | 열 노출 감소 및 모든 하드 제약 검사 |
| P4 | CRUD/API·CSV·대시보드 7화면·모바일 | 전체 로컬 시연 흐름. P5 알림/PDF는 로컬 최소 구현까지 선행 |
| P5 | 모의 알림·판단 기록 PDF·README·배포 | 외부 링크에서 독립 시연 |
| P6 | 발표·촬영 순서·Q&A·한계 | 검증된 내용만 사용한 7분 발표 지원 자료 |

각 단계 종료 후 실제 테스트·수용 기준·직접 확인 항목을 보고하고 git 커밋한다.
다음 단계는 사용자가 요청하기 전 진행하지 않는다.
