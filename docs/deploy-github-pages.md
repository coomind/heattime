# 정적 시연판 GitHub Pages 배포 절차 (준비만, 실행 전 작성자 승인 필요)

정적 시연판은 `frontend/dist-demo`이며 백엔드 없이 동작합니다. 해시 라우팅과 상대 경로(`VITE_BASE=./`)만 써서 `https://<계정>.github.io/<저장소>/` 같은 하위 경로에서도 열립니다. 서비스 워커는 같은 경로 아래의 화면 자산만 저장하고 API는 저장하지 않습니다.

## 준비된 것

- `npm run build:demo`: `frontend/dist-demo` 생성.
- `npm run test:e2e:demo`: `dist-demo`를 `/heattime/` 하위 경로로 띄우고 외부 요청을 모두 막은 채 전체 흐름을 검사.
- `.github/workflows/pages.yml`: 수동 실행(`workflow_dispatch`)만 받는 배포 워크플로. push만으로는 배포되지 않습니다.

## 배포 순서 (작성자가 승인한 뒤)

1. 공개 전 점검 결과(`docs/submission-report.md` 5절)를 확인하고, 저장소 공개 여부를 정합니다. 기상청 자료의 재배포 조건(공공데이터포털 이용허락범위)을 확인합니다.
2. 원격 저장소에 push합니다(에이전트는 승인 없이 push하지 않습니다).
3. GitHub 저장소 Settings → Pages에서 Source를 "GitHub Actions"로 둡니다.
4. Actions 탭에서 "Deploy static demo to GitHub Pages"를 수동 실행합니다.
5. 배포 주소를 `submission/README_심사위원.md`의 링크 줄에 적고 `scripts/package_submission.py`를 다시 실행합니다.

## 로컬에서 같은 결과 확인

```powershell
Push-Location frontend
npm run build:demo
node scripts/serve-static.mjs dist-demo 8128 /heattime/
Pop-Location
```
