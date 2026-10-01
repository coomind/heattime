# B1 새 Windows 복제본 재현

2026-10-02. 로컬 저장소를 --no-hardlinks로 임시 폴더에 새로 clone했다.
C:\Users\coomi\AppData\Local\Temp\heattime-overnight-c32390bb4d244d9ab0bc5ce31a782615
기존.venv/node_modules/DB/실측 샘플/.env를 복사하지 않았다. 복제본 시작 커밋:a175614.

README 명령 그대로 Python 가상환경 생성 → pip install -e ".[dev]" → frontend npm ci/build → backend.run을 실행했다.
Windows Python3.13.9,Node24.19.0,새 pytest9.1.1. 패키지 캐시는 설치 도구가 사용했지만 환경/설치 디렉터리는 새 것이다.
Python 설치 및 프론트 설치 성공, npm 감사0취약점, 빌드 성공(차트 큰 번들 경고는 B5 대상).
서버 실제 시작 및 Chromium 데스크톱·모바일 전체 흐름2개 통과(7.0초).
기존 브라우저 바이너리는 사용자 공용 캐시에 이미 설치되어 있었다. 새 PC에는 README의 playwright install chromium이 필요하다.
새 복제본 전체 pytest100개 통과. TestClient 사용 중단 예정 경고는 B5에서 동작 변경 위험 여부를 검토한다.
.env를 읽거나 출력하지 않았다. 외부 기상 API·수집·배포·실제 메시지 발송·로그인은 수행하지 않았다.

설치/실행을 막는 문제는 없어 README 실행 절차를 바꾸지 않았다.
확인 항목: 다른 Windows PC에서 지원Python/Node 버전 및 최초Chromium 설치, 포트8000 충돌 여부 확인.
임시 복제본을 보존했으며 사용자의 기존 미추적 파일(=)을 수정/삭제/커밋하지 않았다.
