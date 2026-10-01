# 구현 계획

사용자가 지정한 docs/spec.md가 유일한 기준 명세다. 아래는 그 명세의 구현 순서다.

## 기술 스택

- Python 3.11+ / FastAPI / SQLite, 시연 우선
- React + Vite + JavaScript(JSX) / Recharts, 모바일 대응
- pvlib(일사량), OR-Tools CP-SAT(재편성), pytest
- WBGT: lwbgt1.0.1 공개 Liljegren 구현, 라이선스 원문 보존
- PDF: ReportLab + NanumGothic 포함. 호스팅: Render 설정 준비, 사용자 지시로 실제 배포 제외
- P1은 의존성을 줄여 표준 라이브러리만 사용. 이후 필요한 단계에서 패키지 추가

## 폴더

```text
AGENTS.md                  작업 규칙
.env.example               빈 키 자리 (.env 읽기 금지)
backend/
  weather/                 P1 데이터 모델·어댑터·격자·저장·실행 도구
  engine/                  P2 구현 완료
  schedule/                P3 구현 완료
frontend/                  P4 구현 완료
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
| P5 | 모의 알림·판단 기록 PDF·README·배포 | 사용자 변경 범위: 배포 설정·절차와 로컬 전체 흐름 (외부 배포 제외) |
| P6 | 발표·촬영 순서·Q&A·한계 | 검증된 내용만 사용한 7분 발표 지원 자료 |

각 단계 종료 후 실제 테스트·수용 기준·직접 확인 항목을 보고하고 git 커밋한다.
사용자 후속 지시에 따라 P2~P6 단계 사이에 멈추지 않고 진행. P6 및 최종 보고 후 종료한다.

최종 구현 구조: backend/app.py·service.py·repository.py / weather·engine·schedule / notifications.py·exports.py·run.py / frontend/src·e2e / docs/presentation / Dockerfile·render.yaml.
프론트는 작은 시연 범위에 맞춰 JSX로 구현했다. 명세는 React를 권장하며 TypeScript는 필수 기준이 아니다.
