# HeatTime 심사위원 안내

HeatTime은 생활체육과 유소년 축구 대회 운영자를 위한 폭염 경기 운영 의사결정 보조 도구입니다. 대회, 팀, 구장, 연락처는 모두 가상 예시이고, WBGT는 기상청 관측 자료로 계산한 추정값입니다. 가상 대회로 검증한 시제품이며 현장 실측과 도입 실적은 없습니다.

## 30초 안에 시연 열기

1. 링크로 열기: https://coomind.github.io/heattime/ (GitHub Pages 정적 시연판, 백엔드 없음). 첫 화면이 8월 10일 대시보드입니다.
2. 인터넷 없이 열기(Node.js 필요): 소스 압축을 풀고 `frontend` 폴더에서 아래 한 줄을 실행한 뒤 브라우저로 http://127.0.0.1:8128/heattime/ 을 엽니다. `dist-demo`가 없으면 먼저 `npm ci` 와 `npm run build:demo` 를 실행합니다.

```
node scripts/serve-static.mjs dist-demo 8128 /heattime/
```

3. 전체 서버로 열기(Python 3.13, Node.js 22): 저장소 README의 "설치와 실행"을 따른 뒤 http://127.0.0.1:8000/#live 를 엽니다.

## 시연 순서와 볼 것

| 순서 | 화면 | 볼 것 |
|---|---|---|
| 1 | 대시보드(첫 화면, 2026-08-10) | 원래 일정 15경기 중 4경기가 운동 중지 단계입니다. 칸의 큰 숫자가 판정값이고 작은 글씨가 추정 범위입니다. |
| 2 | 경기 상세 | 2조 2경기의 판정값: 관측 기반 추정 28.774 + 구장 보정 2.5 = 중앙 추정 31.274 → 판정값 31.3℃ (단계 4) |
| 3 | 재편성 실행 | 15경기 배정, 0경기 연기. 공통 15경기의 열 노출 점수 5,273 → 4,153(일정 비교용 내부 점수) |
| 4 | 재편성 비교 | 원래 일정이 어기는 제약 목록, 바뀐 경기 목록, 원래와 제안 일정표 |
| 5 | 판단 사유 입력과 승인 | 최종 판단은 운영자가 합니다. 시연판은 미리 만든 기록과 같은 사유로만 승인합니다. |
| 6 | 알림 로그 | 모의 알림 48건. 실제 문자나 카카오 메시지는 보내지 않습니다. |
| 7 | 운영 기록 | 사전 생성된 시연용 PDF와 CSV, 지금 상태의 JSON 내려받기 |
| 8 | 참가팀 일정 | 읽기 전용 일정(휴대폰 화면) |
| 9 | 재현 모드에서 8월 8일 | 원래 단계 0 · 0 · 1 · 0 · 14, 10경기 배정, 5경기 연기(결승, 1조 2경기, 4조 1경기, 준결승 1, 준결승 2). 연기 상자의 '이틀 일정으로 다시 짜면'을 누르면 8월 8~9일 이틀 일정으로 15경기 배정, 0경기 연기 장면이 열립니다. |

## 판정 기준

관측 기반 WBGT 추정에 구장 보정 +2.5℃를 더한 중앙 추정을 판정값으로 씁니다. 단계 경계는 21, 25, 28, 31℃입니다(일본 환경성 지침). 추정 범위(중앙 ±1.5℃)는 참고로 표시하고 판정에 쓰지 않습니다. 구장 보정값은 해외 연구를 바탕으로 한 설계 가정이며 국내 구장에서 검증하지 않았습니다.

## 검증한 것과 하지 않은 것

| 항목 | 상태 |
|---|---|
| 기상청 관측 62일(2026-07-01~08-31)로 같은 가상 대회 재현 | 했음. 배정 699 / 연기 231 (전체 930경기) |
| 재편성 결과의 제약(구장 정리, 팀 휴식, 선행 경기, 운영 시간) 검사 | 했음. 자동 테스트로 확인 |
| 오프라인 정적 시연판 전체 흐름 | 했음. 네트워크를 막은 브라우저 자동 시험 |
| 현장 WBGT 측정값과 대조 | 하지 않음 |
| 국내 구장 보정값(+2.5℃) 검증 | 하지 않음 |
| 대회 운영자 인터뷰 | 하지 않음 |
| 실시간 예보 연동 | 하지 않음(관측 재현만) |
| 외부 배포 | 정적 시연판만 GitHub Pages에 배포함(https://coomind.github.io/heattime/). 서버 기능은 배포하지 않음 |

## 이 폴더

- `screenshots/`: 화면 캡처(번호_화면_폭). `video-check/`는 활용 영상 검수 프레임입니다.
- `HeatTime_source.zip`: 소스 372개 파일. 아래 제외 목록을 뺐습니다.
- `licenses/`: 의존성 라이선스와 기상 자료 출처. `sources.md`: 근거 기사와 정책 출처.
- `deck/`, `site/`, `media/`: 발표자료, 소개 사이트, 활용 영상(작성자가 incoming/에 넣은 최신 파일을 복사).

### 소스 압축에서 뺀 것

- `.env`
- `.env.*`
- `.venv/*`
- `*/node_modules/*`
- `node_modules/*`
- `frontend/dist/*`
- `frontend/dist-demo/*`
- `*.sqlite3`
- `*.sqlite3-*`
- `data/output/*`
- `incoming/*`
- `recordings/*`
- `submission/*`
- `data/samples/*`
- `data/observations/*`
- `tests/fixtures/aws-*.txt`
- `docs/kma/*.docx`
- `docs/kma/live-connection-verification.json`

### 이번 실행에서 복사한 파일

- deck/HeatTime_7분발표.pptx ← incoming/HeatTime_7분발표.pptx
- deck/HeatTime_7분발표.pdf ← incoming/HeatTime_7분발표.pdf
- site/HeatTime_소개사이트.html ← incoming/HeatTime_소개사이트.html
- media/intro.mp4 ← incoming/video_kit (1)/intro.mp4
- media/outro.mp4 ← incoming/video_kit (1)/outro.mp4
- media/demo_bed.m4a ← incoming/video_kit (1)/demo_bed.m4a
- media/HeatTime_활용영상.mp4 ← recordings/final/HeatTime_활용영상.mp4
- media/HeatTime_활용영상_720p.mp4 ← recordings/final/HeatTime_활용영상_720p.mp4
- site/HeatTime_활용영상_720p.mp4 ← media/

### 사용자가 넣을 파일

- 없음
