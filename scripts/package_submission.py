"""Build submission/ for the competition and ../HeatTime_제출패키지.zip. Safe to re-run any time.

Every run copies the newest presentation, intro site and video kit from incoming/ (the author replaces
them later), regenerates README_심사위원.md from data/output/demo-numbers.json, and rebuilds the source zip.
Never reads .env. Never uploads or sends anything.
"""
import fnmatch
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT/'submission'
INCOMING = ROOT/'incoming'
NUMBERS = ROOT/'data/output/demo-numbers.json'
CAPTURES = ROOT/'data/output/captures'
VIDEO = ROOT/'recordings/final'
OUTER_ZIP = ROOT.parent/'HeatTime_제출패키지.zip'

# Source zip: tracked and new (not ignored) files, minus these patterns.
EXCLUDE = ['.env', '.env.*', '.venv/*', '*/node_modules/*', 'node_modules/*', 'frontend/dist/*', 'frontend/dist-demo/*',
           '*.sqlite3', '*.sqlite3-*', 'data/output/*', 'incoming/*', 'recordings/*', 'submission/*',
           # Raw or near-raw KMA API material whose redistribution terms are not confirmed in this repository.
           'data/samples/*', 'data/observations/*', 'tests/fixtures/aws-*.txt', 'docs/kma/*.docx',
           'docs/kma/live-connection-verification.json']
KEEP_EXAMPLE = ['.env.example', 'data/samples/README.md']

DEPENDENCIES_NOTE = {
    'lwbgt': 'WBGT 계산 (Liljegren 모델 공개 구현). Apache-2.0과 Argonne WBGT 1.1 고지 포함',
    'ortools': '경기 재편성 최적화 (CP-SAT)', 'pvlib': '태양 위치와 맑은 하늘 일사 추정',
    'reportlab': '운영 기록 PDF', 'fastapi': '백엔드 API', 'react': '화면', 'recharts': '그래프',
    '@fontsource/ibm-plex-sans-kr': '화면 한글 서체 원본 (서브셋으로 포함)', '@fontsource/ibm-plex-mono': '숫자 서체',
}


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True, encoding='utf-8').stdout


def newest(pattern):
    found = sorted(INCOMING.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True) if INCOMING.exists() else []
    return found[0] if found else None


def copy_incoming():
    """incoming/ -> submission/{deck,site,media}. Picks the newest match so '파일 (2).html' style names also work."""
    plan = {'deck': [('HeatTime_7분발표*.pptx', 'HeatTime_7분발표.pptx'), ('HeatTime_7분발표*.pdf', 'HeatTime_7분발표.pdf')],
            'site': [('HeatTime_소개사이트*.html', 'HeatTime_소개사이트.html')]}
    copied, missing = [], []
    for folder, items in plan.items():
        (SUB/folder).mkdir(parents=True, exist_ok=True)
        for pattern, name in items:
            src = newest(pattern)
            if src: shutil.copy2(src, SUB/folder/name); copied.append(f'{folder}/{name} ← incoming/{src.name}')
            else: missing.append(f'{folder}/{name} (incoming/{pattern})')
    kit = newest('video_kit*')
    (SUB/'media').mkdir(parents=True, exist_ok=True)
    for name in ('intro.mp4', 'outro.mp4', 'demo_bed.m4a'):
        src = kit/name if kit else None
        if src and src.exists(): shutil.copy2(src, SUB/'media'/name); copied.append(f'media/{name} ← incoming/{kit.name}/{name}')
        else: missing.append(f'media/{name} (incoming/video_kit/{name})')
    for name in ('HeatTime_활용영상.mp4', 'HeatTime_활용영상_720p.mp4'):
        src = VIDEO/name
        if src.exists(): shutil.copy2(src, SUB/'media'/name); copied.append(f'media/{name} ← recordings/final/{name}')
        else: missing.append(f'media/{name} (scripts/demo-video 녹화 후 생성)')
    if (SUB/'media/HeatTime_활용영상_720p.mp4').exists():
        shutil.copy2(SUB/'media/HeatTime_활용영상_720p.mp4', SUB/'site/HeatTime_활용영상_720p.mp4'); copied.append('site/HeatTime_활용영상_720p.mp4 ← media/')
    else: missing.append('site/HeatTime_활용영상_720p.mp4 (소개 사이트가 같은 폴더에서 재생)')
    return copied, missing


def copy_screenshots():
    target = SUB/'screenshots'; target.mkdir(parents=True, exist_ok=True)
    for old in target.glob('*.png'): old.unlink()
    files = sorted(CAPTURES.glob('*/*.png')) if CAPTURES.exists() else []
    for f in files: shutil.copy2(f, target/f'{f.stem}_{f.parent.name}.png')
    check = ROOT/'recordings/video-check'
    if check.exists():
        (target/'video-check').mkdir(exist_ok=True)
        for f in sorted(check.glob('*.png')): shutil.copy2(f, target/'video-check'/f.name)
    return [p.name for p in sorted(target.glob('*.png'))]


def source_files():
    names = run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z']).split('\0')
    keep = []
    for n in sorted(set(filter(None, names))):
        if not (ROOT/n).is_file(): continue
        if n in KEEP_EXAMPLE or not any(fnmatch.fnmatch(n, pat) for pat in EXCLUDE): keep.append(n)
    return keep


def source_zip():
    files = source_files(); target = SUB/'HeatTime_source.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in files: z.write(ROOT/n, 'HeatTime/' + n)
    names = set(files)
    assert '.env' not in names and not any(n.startswith('.venv/') or '/node_modules/' in n for n in names)
    return target, len(files)


def licenses():
    out = SUB/'licenses'; out.mkdir(parents=True, exist_ok=True)
    from importlib.metadata import metadata, PackageNotFoundError
    rows = []
    for name in ['lwbgt', 'ortools', 'pvlib', 'PyYAML', 'matplotlib', 'fastapi', 'uvicorn', 'reportlab', 'httpx']:
        try:
            md = metadata(name)
            lic = md.get('License-Expression') or next((c.split('::')[-1].strip() for c in md.get_all('Classifier') or [] if c.startswith('License ::')), None) or (md.get('License') or '').split('\n')[0][:80]
            rows.append(('Python', name, md['Version'], lic or '패키지 정보에 없음', DEPENDENCIES_NOTE.get(name.lower(), '')))
        except PackageNotFoundError:
            rows.append(('Python', name, '?', '설치 안 됨', ''))
    pkg = json.loads((ROOT/'frontend/package.json').read_text(encoding='utf-8'))
    for name in [*pkg['dependencies'], *pkg['devDependencies']]:
        p = ROOT/'frontend/node_modules'/name/'package.json'
        info = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rows.append(('npm', name, info.get('version', '?'), info.get('license', '?'), DEPENDENCIES_NOTE.get(name, '개발·시험용' if name in pkg['devDependencies'] else '')))
    rows += [('서체', 'IBM Plex Sans KR (서브셋)', '@fontsource 5.x', 'OFL-1.1', '화면 글꼴, KS X 1001 한글과 앱 문구만 남긴 WOFF'),
             ('서체', 'IBM Plex Mono', '@fontsource 5.x', 'OFL-1.1', '숫자 글꼴'),
             ('서체', 'NanumGothic', 'backend/assets/fonts', 'OFL-1.1', 'PDF 한글 글꼴')]
    copies = {'lwbgt-Apache-2.0.txt': ROOT/'docs/licenses/lwbgt-Apache-2.0.txt', 'lwbgt-NOTICE.txt': ROOT/'docs/licenses/lwbgt-NOTICE.txt',
              'Liljegren-WBGT-1.1.txt': ROOT/'docs/licenses/Liljegren-WBGT-1.1.txt', 'dejavu-font-license.txt': ROOT/'docs/licenses/dejavu-font-license.txt',
              'NanumGothic-OFL.txt': ROOT/'backend/assets/fonts/OFL.txt',
              'IBM-Plex-Sans-KR-OFL.txt': ROOT/'frontend/node_modules/@fontsource/ibm-plex-sans-kr/LICENSE',
              'IBM-Plex-Mono-OFL.txt': ROOT/'frontend/node_modules/@fontsource/ibm-plex-mono/LICENSE'}
    for name, src in copies.items():
        if src.exists(): shutil.copy2(src, out/name)
    lines = ['# 의존성 라이선스와 자료 출처', '', '설치된 패키지 정보에서 자동으로 뽑은 목록입니다(`scripts/package_submission.py`). 전이 의존성은 각 패키지의 라이선스를 따릅니다.', '',
             '| 구분 | 이름 | 버전 | 라이선스 | 용도 |', '|---|---|---|---|---|'] + [f'| {a} | {b} | {c} | {d} | {e} |' for a, b, c, d, e in rows]
    lines += ['', '## 고지', '', '- This product includes software produced by UChicago Argonne, LLC under Contract No. DE-AC02-06CH11357 with the Department of Energy.',
              '- 라이선스 원문은 이 폴더의 txt 파일에 있습니다.', '',
              '## 기상 자료 출처', '',
              '- 기상청 지상(종관, ASOS) 시간자료 조회서비스(공공데이터포털 오픈API), 수원 지점 119, 2026-07-01~2026-08-31 시간자료. 앱의 시연 장면은 이 관측값으로 계산한 WBGT 추정을 담고 있습니다.',
              '- 최신 관측 연결 시험(1회)은 기상청 API허브 방재기상관측(AWS) 분 자료를 사용했습니다.',
              '- 출처 표기: "자료: 기상청". 공공데이터포털의 이용허락범위는 제출 전에 다시 확인해야 합니다(이 저장소에는 확인 기록이 없습니다).',
              '- 원본 응답, 정규화한 관측 파일, 기상청 활용가이드 문서는 재배포 조건이 확인되지 않아 소스 압축에서 뺐습니다.']
    (out/'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return len(rows)


def sources_md():
    import re
    text = (ROOT/'frontend/src/BackgroundEvidence.jsx').read_text(encoding='utf-8')
    links = re.findall(r"url:'([^']+)'", text)
    titles = re.findall(r"source:'([^']+)'", text)
    lines = ['# 근거 출처', '', '앱의 근거 화면에 넣은 기사와 정책 자료입니다. 기사 문구는 원문 확인 후 원문에 맞춰 줄였습니다.', '', '## 배경 기사', '']
    lines += [f'- {t}: {u}' for t, u in zip(titles, links)] if titles and len(titles) == len(links) else [f'- {u}' for u in links]
    lines += ['', '## 정책과 계산 근거', '',
              '- 일반 운동 WBGT 단계(21/25/28/31℃): 일본 환경성 열사병 예방 정보, https://www.wbgt.env.go.jp/en/sp/wbgt.php',
              '- 축구 열 지침(WBGT 26℃ 초과 냉각, 28℃ 초과 경기 중단): FIFPRO, https://media.fifpro.org/media/ltio1czh/heat-guidelines_en-1.pdf',
              '- WBGT 계산 모델: Liljegren JC, Carhart RA, Lawday P, Tschopp S, Sharp R (2008), Modeling the Wet Bulb Globe Temperature Using Standard Meteorological Measurements, Journal of Occupational and Environmental Hygiene 5(10):645-655, https://doi.org/10.1080/15459620802310770',
              '- 공개 구현: lwbgt 1.0.1, https://github.com/zyf0717/lwbgt',
              '- 기상 자료: 기상청 지상(종관, ASOS) 시간자료 조회서비스, 수원 119']
    (SUB/'sources.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def judge_readme(numbers, zip_files, copied, missing):
    S = {s['key']: s for s in numbers['scenes']}; d, e, t = S['demo'], S['extreme'], S['extreme-2day']
    lv = lambda xs: ' · '.join(map(str, xs))
    lines = ['# HeatTime 심사위원 안내', '',
             'HeatTime은 생활체육과 유소년 축구 대회 운영자를 위한 폭염 경기 운영 의사결정 보조 도구입니다. 대회, 팀, 구장, 연락처는 모두 가상 예시이고, WBGT는 기상청 관측 자료로 계산한 추정값입니다. 가상 대회로 검증한 시제품이며 현장 실측과 도입 실적은 없습니다.', '',
             '## 30초 안에 시연 열기', '',
             '1. 링크로 열기: https://coomind.github.io/heattime/ (GitHub Pages 정적 시연판, 백엔드 없음). 첫 화면이 8월 10일 대시보드입니다.',
             '2. 인터넷 없이 열기(Node.js 필요): 소스 압축을 풀고 `frontend` 폴더에서 아래 한 줄을 실행한 뒤 브라우저로 http://127.0.0.1:8128/heattime/ 을 엽니다. `dist-demo`가 없으면 먼저 `npm ci` 와 `npm run build:demo` 를 실행합니다.', '',
             '```', 'node scripts/serve-static.mjs dist-demo 8128 /heattime/', '```', '',
             '3. 전체 서버로 열기(Python 3.13, Node.js 22): 저장소 README의 "설치와 실행"을 따른 뒤 http://127.0.0.1:8000/#live 를 엽니다.', '',
             '## 시연 순서와 볼 것', '',
             f"| 순서 | 화면 | 볼 것 |", '|---|---|---|',
             f"| 1 | 대시보드(첫 화면, {d['date']}) | 원래 일정 15경기 중 {d['original_levels'][4]}경기가 운동 중지 단계입니다. 칸의 큰 숫자가 판정값이고 작은 글씨가 추정 범위입니다. |",
             f"| 2 | 경기 상세 | {d['decision_example']['match']}의 판정값: {d['decision_example']['formula']} |",
             f"| 3 | 재편성 실행 | {d['assigned']}경기 배정, {d['postponed']}경기 연기. 공통 {d['heat']['common_matches']}경기의 열 노출 점수 {d['heat']['original']:,} → {d['heat']['proposed']:,}(일정 비교용 내부 점수) |",
             '| 4 | 재편성 비교 | 원래 일정이 어기는 제약 목록, 바뀐 경기 목록, 원래와 제안 일정표 |',
             '| 5 | 판단 사유 입력과 승인 | 최종 판단은 운영자가 합니다. 시연판은 미리 만든 기록과 같은 사유로만 승인합니다. |',
             f"| 6 | 알림 로그 | 모의 알림 {d['notifications']}건. 실제 문자나 카카오 메시지는 보내지 않습니다. |",
             '| 7 | 운영 기록 | 사전 생성된 시연용 PDF와 CSV, 지금 상태의 JSON 내려받기 |',
             '| 8 | 참가팀 일정 | 읽기 전용 일정(휴대폰 화면) |',
             f"| 9 | 재현 모드에서 8월 8일 | 원래 단계 {lv(e['original_levels'])}, {e['assigned']}경기 배정, {e['postponed']}경기 연기({', '.join(p['name'] for p in e['postponed_matches'])}). 연기 상자의 '이틀 일정으로 다시 짜면'을 누르면 8월 8~9일 이틀 일정으로 {t['assigned']}경기 배정, {t['postponed']}경기 연기 장면이 열립니다. |", '',
             '## 판정 기준', '',
             f"관측 기반 WBGT 추정에 구장 보정 +{numbers['criteria']['venue_offset_c'][0]}℃를 더한 중앙 추정을 판정값으로 씁니다. 단계 경계는 {', '.join(map(str, numbers['criteria']['boundaries_c']))}℃입니다(일본 환경성 지침). 추정 범위(중앙 ±{numbers['criteria']['uncertainty_c']}℃)는 참고로 표시하고 판정에 쓰지 않습니다. 구장 보정값은 해외 연구를 바탕으로 한 설계 가정이며 국내 구장에서 검증하지 않았습니다.", '',
             '## 검증한 것과 하지 않은 것', '',
             '| 항목 | 상태 |', '|---|---|',
             f"| 기상청 관측 62일(2026-07-01~08-31)로 같은 가상 대회 재현 | 했음. 배정 {numbers['period']['assigned_total']} / 연기 {numbers['period']['postponed_total']} (전체 {numbers['period']['matches_total']}경기) |",
             '| 재편성 결과의 제약(구장 정리, 팀 휴식, 선행 경기, 운영 시간) 검사 | 했음. 자동 테스트로 확인 |',
             '| 오프라인 정적 시연판 전체 흐름 | 했음. 네트워크를 막은 브라우저 자동 시험 |',
             '| 현장 WBGT 측정값과 대조 | 하지 않음 |', '| 국내 구장 보정값(+2.5℃) 검증 | 하지 않음 |',
             '| 대회 운영자 인터뷰 | 하지 않음 |', '| 실시간 예보 연동 | 하지 않음(관측 재현만) |',
             '| 외부 배포 | 정적 시연판만 GitHub Pages에 배포함(https://coomind.github.io/heattime/). 서버 기능은 배포하지 않음 |', '',
             '## 이 폴더', '',
             '- `screenshots/`: 화면 캡처(번호_화면_폭). `video-check/`는 활용 영상 검수 프레임입니다.',
             f'- `HeatTime_source.zip`: 소스 {zip_files}개 파일. 아래 제외 목록을 뺐습니다.',
             '- `licenses/`: 의존성 라이선스와 기상 자료 출처. `sources.md`: 근거 기사와 정책 출처.',
             '- `deck/`, `site/`, `media/`: 발표자료, 소개 사이트, 활용 영상(작성자가 incoming/에 넣은 최신 파일을 복사).', '',
             '### 소스 압축에서 뺀 것', ''] + [f'- `{p}`' for p in EXCLUDE] + ['', '### 이번 실행에서 복사한 파일', ''] + [f'- {c}' for c in copied] + \
            ['', '### 사용자가 넣을 파일', ''] + ([f'- {m}' for m in missing] or ['- 없음'])
    (SUB/'README_심사위원.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


CHECKLIST = """# 제출 전 체크리스트 (사람이 할 일)

- [ ] 새 발표자료(pptx, pdf)와 소개 사이트(html)를 `incoming/`에 넣고 `.\\.venv\\Scripts\\python.exe scripts/package_submission.py`를 다시 실행한다.
- [ ] 활용 영상 최종본(`submission/media/HeatTime_활용영상.mp4`)을 처음부터 끝까지 보고 승인한다.
- [ ] 발표자료 표지에 발표자 이름을 넣는다.
- [ ] 공모전 사무국(02-6953-1510)에 업로드 형식, 용량 제한, 제출 후 수정 가능 여부를 문의한다.
- [ ] 접수 계정을 만들고 제출 양식을 미리 본다.
- [x] 정적 시연 링크 배포 승인 및 배포 완료(https://coomind.github.io/heattime/, 2026-10-21).
- [ ] 7분 발표를 리허설한다.
- [ ] 10월 29일까지 제출한다(마감 2026-10-30 18:00).
- [ ] 11월 20일 발표에 쓸 노트북에서 오프라인 시연을 점검한다(인터넷을 끄고 `node scripts/serve-static.mjs dist-demo 8128 /heattime/`).
"""


def main():
    if not NUMBERS.exists():
        sys.exit('data/output/demo-numbers.json이 없습니다. 먼저 scripts/export_demo_numbers.py를 실행하세요.')
    numbers = json.loads(NUMBERS.read_text(encoding='utf-8'))
    SUB.mkdir(exist_ok=True)
    copied, missing = copy_incoming()
    shots = copy_screenshots()
    target, count = source_zip()
    licenses(); sources_md()
    (SUB/'CHECKLIST.md').write_text(CHECKLIST, encoding='utf-8')
    judge_readme(numbers, count, copied, missing)
    if OUTER_ZIP.exists(): OUTER_ZIP.unlink()
    with zipfile.ZipFile(OUTER_ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SUB.rglob('*')):
            if f.is_file(): z.write(f, 'submission/' + f.relative_to(SUB).as_posix())
    print(json.dumps({'source_zip': str(target.relative_to(ROOT)), 'source_files': count, 'source_zip_bytes': target.stat().st_size,
                      'screenshots': len(shots), 'copied': copied, 'missing': missing,
                      'package_zip': str(OUTER_ZIP), 'package_zip_bytes': OUTER_ZIP.stat().st_size,
                      'package_sha256': hashlib.sha256(OUTER_ZIP.read_bytes()).hexdigest()}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
