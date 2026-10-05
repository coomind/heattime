# 알고리즘 비교 재현

프로젝트 가상환경과 커밋된 기상 관측 정규화 파일·고정 제안 원장만 사용한다. API·키·.env·로그인·외부 통신이 필요 없다. 정책과 기존62일 결과·시연 후보·관측 스냅샷은 변경하지 않는다.

```powershell
.\.venv\Scripts\python.exe scripts/compare_schedule_methods.py
.\.venv\Scripts\python.exe -m pytest tests/test_competition_comparison.py -q
```

정규화 관측에서 새 입력·위험도를 만들고 원장의 입력 지문과 일치해야 비교한다. 한 항목이라도 다르면 중단한다. 동일 하드 제약으로 기존 탐욕 폴백을 실행하고 양쪽 배정·기간·쿨링·단계·점수를 검증한다. 결과는 docs/competition-evidence/method-comparison.json에 기록한다. DB는 data/output/competition/ 아래의 별도 파일이다.

최초 원장은 지난 실제 자료 작업에서 이미 계산한62개 날짜별 세션으로 만들었다. 최초 추출 명령은 아래와 같다. 기존 원장을 재생성할 목적이 아니라면 실행하지 않는다.

```powershell
.\.venv\Scripts\python.exe scripts/compare_schedule_methods.py --source-sessions data/output/real
```

추출은 기존 공개62일 결과의 날짜·배정·연기·원래/제안 점수·솔버 상태와 일치할 때만 허용한다. 수집 스크립트가 아니며 CP-SAT 재풀이도 하지 않는다. 외부 제출에는 원본 API 응답이나 개인 정보를 넣지 않는다.

경기 배정 합계는62개 가상 대회에서 발생한 배정 건수다. 실제 참가자·실제 대회에서 살린 경기 수가 아니다. 측정한 탐욕 실행 시간은 개발 PC의 실행값이며 사람의 업무 시간이나 서비스 응답 보장이 아니다.
