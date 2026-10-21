# P1 완료 보고 (2026-10-01)

> 이전 기준 기록입니다(2026-10-21 이전: 유소년 범위 상단 판정). 현재 수치와 기준은 [2026-10-21 재계산](recalc-2026-10-21.md)을 보세요. 2026-10-11 재계산(일사 구간 정렬·판정값 0.1℃ 반올림·동점 처리 고정) 기록은 [2026-10-11 재계산](recalc-2026-10-11.md)에 있습니다.

## 변경 파일

- git 초기화, .gitignore(.env 및 실제 응답 샘플 제외), 빈 KMA_API_KEY의 .env.example
- docs/spec.md: 첨부 파일을 바이트 단위로 그대로 복사 (SHA-256 일치 확인)
- AGENTS.md: 명세 4.1 절대 규칙 및 사용자 지정 작업 방식
- backend/weather/: 내부 데이터 모델, 공식 격자 양방향 변환, 어댑터, SQLite 저장, mock 실행 도구
- data/mock/venues.json: 수원 지역 가상 구장 3곳. 실제 구장 위치/지점으로 주장하지 않음
- tests/: 격자 공식 함수 대조, 수집·저장·검증·오프라인 검사
- README.md, docs/plan.md, docs/p1-checklist.md, data/samples/README.md
- P2/P3/P4 폴더는 빈 자리만 생성. 후속 기능은 구현하지 않음

## 실제 실행 결과

환경: Windows, Python 3.13.9, pytest 8.4.2.

- python -m pytest -q: 30 passed
- python -m backend.weather.cli --date 2026-08-01: 구장 3곳 / 예보 mock 72건 저장
- python -m backend.weather.cli --date 2026-08-01 --provider asos: 구장 3곳 / ASOS mock 72건 저장
- SQLite 직접 조회: kma_fcst 72건/3곳, asos_obs 72건/3곳 (합계 144건)
- 같은 날짜 재수집의 중복 방지, KST 24시간, 외래키와 원자적 저장 테스트 통과
- 수동 WBGT는 별도 실측 테이블에 저장하며 기온으로 위조하지 않음
- mock 실행에서 .env 읽기 및 네트워크 접근이 없는지 차단 테스트 통과
- git ignore 확인: .env, .env.local, SQLite, 실제 응답 샘플 제외

## 수용 기준

**통과:** mock 모드로 구장 3곳 × 24시간 자료 저장, 전체 테스트 통과.
실제 API 연결 및 실제 관측 기반 재현은 아직 미구현이다.
격자 변환은 공식 공개 함수 실행값 5곳과 대조했고 왕복·범위 검사도 통과했다.
TODO: 공식 좌표표/실제 변환 응답을 통한 독립 기준 대조.

## 직접 확인할 항목

1. README의 mock 실행을 재현하고 결과가 각 공급자 72건인지 확인
2. 가상 구장 이름과 기본 시연 날짜를 원하는 예시로 쓸지 확인
3. 실제 응답 확보 시 인증키를 제거해 data/samples/에 넣고 공식 문서를 함께 제공
4. ASOS 지점과 일사량 단위·누적 기간 확인 (docs/p1-checklist.md)

기상청 공개 변환 함수 출처: https://www.weather.go.kr/w/resources/js/fn.js
mock ASOS 일사량은 합성값이므로 실제 관측 오차 검증 근거로 사용할 수 없다.
P1 종료 후 멈추며 P2는 사용자의 다음 요청 때 진행한다.
