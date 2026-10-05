"""Build an offline claim ledger from frozen evidence and actual test receipts.

No credentials, network calls, engine recalculation or user-record publication.
"""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
from check_competition_evidence import run as check_competition
from check_submission import run as check_submission
from check_presentation import run as check_presentation, ASSUMPTIONS
from backend.weather.asos_samples import load_dataset
from backend.weather.models import KST
from check_no_field_evidence import run as check_no_field
from check_tournament_scale import run as check_scale


def junit_receipt(path):
    root = ET.parse(path).getroot()
    cases = root.findall('.//testcase')
    failures = len(root.findall('.//failure')) + len(root.findall('.//error'))
    skipped = len(root.findall('.//skipped'))
    failed_attributes = any(int(s.get(k, '0')) for s in root.iter('testsuite') for k in ('failures', 'errors', 'skipped'))
    if not cases or failures or skipped or failed_attributes:
        raise ValueError('완료·전부 통과한 테스트 영수증이 필요합니다.')
    suites = root.findall('./testsuite')
    duration = sum(float(s.get('time', 0)) for s in suites) if suites else sum(float(c.get('time', 0)) for c in cases)
    return {'passed': len(cases), 'failed': failures, 'skipped': skipped, 'duration_seconds': round(duration, 3)}


def browser_receipt(path):
    stats = json.loads(path.read_text(encoding='utf-8-sig'))['stats']
    if not stats['expected'] or any(stats[k] for k in ('unexpected', 'flaky', 'skipped')):
        raise ValueError('재시도 실패·중단 없는 브라우저 검증 영수증이 필요합니다.')
    return {'passed': stats['expected'], 'failed': stats['unexpected'], 'skipped': stats['skipped'],
            'flaky': stats['flaky'], 'duration_seconds': round(stats['duration']/1000, 3)}


def source_fingerprint():
    extensions = {'.py', '.js', '.jsx', '.json', '.yaml', '.yml', '.css', '.html', '.c', '.txt'}
    paths = [p for folder in ('backend', 'frontend/src', 'frontend/e2e', 'frontend/tests', 'scripts', 'tests')
             for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in extensions
             and not p.name.startswith('.env') and '__pycache__' not in p.parts]
    paths += [ROOT/'pyproject.toml', ROOT/'frontend/package.json', ROOT/'frontend/package-lock.json', ROOT/'frontend/playwright.config.js', ROOT/'frontend/vite.config.js']
    rows = [(p.relative_to(ROOT).as_posix(), hashlib.sha256(p.read_text(encoding='utf-8-sig').replace('\r\n', '\n').encode()).hexdigest()) for p in sorted(set(paths)) if p.exists()]
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def collect():
    stamp_path = ROOT/'data/output/award-validation-source.json'
    stamp = json.loads(stamp_path.read_text(encoding='utf-8'))
    if stamp['source_fingerprint'] != source_fingerprint():
        raise ValueError('검사 시작 이후 코드가 변경되었습니다. 최종 코드로 전체 검사를 다시 실행하세요.')
    receipt_paths = [ROOT/'data/output'/name for name in ('award-validation-pytest.xml', 'award-validation-node.xml', 'award-validation-playwright.json')]
    if any(p.stat().st_mtime_ns < stamp_path.stat().st_mtime_ns for p in receipt_paths):
        raise ValueError('검사 시작보다 오래된 영수증입니다. 전체 검사를 다시 실행하세요.')
    checked = {'presentation': check_presentation(write_timing=False), 'submission': check_submission(), 'competition': check_competition(), 'no_field':check_no_field(), 'scale':check_scale()}
    if any(not value['passed'] for value in checked.values()):
        raise ValueError('기존 원고·수치 정합성 검사에 실패했습니다. 증거 자료를 갱신하지 않습니다.')
    receipts = {'python': junit_receipt(ROOT/'data/output/award-validation-pytest.xml'),
                'node': junit_receipt(ROOT/'data/output/award-validation-node.xml'),
                'browser': browser_receipt(ROOT/'data/output/award-validation-playwright.json')}
    if any(receipts[k]['passed'] < minimum for k, minimum in [('python', 900), ('node', 27), ('browser', 138)]):
        raise ValueError('기존 검사 수보다 적은 영수증입니다. 전체 검사를 실행하세요.')
    def read(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))
    replay = read('docs/real-data/replay-results.json')
    comparison = read('docs/competition-evidence/method-comparison.json')['summary']
    no_field = read('docs/competition-evidence/no-field-analysis.json')['summary']
    scale = read('docs/competition-evidence/tournament-scale-analysis.json')['summary']
    live = read('docs/kma/live-connection-verification.json')
    sample = load_dataset()
    if sample.original_sha256 != replay['original_sample_sha256']:
        raise ValueError('현재 관측 입력과 고정 분석의 원자료 지문이 다릅니다.')
    paths = ['docs/real-data/replay-results.json', 'docs/competition-evidence/method-comparison.json',
             'docs/competition-evidence/frozen-solutions.json', 'docs/kma/live-connection-verification.json',
             'frontend/src/demo/observed-snapshot.json', 'frontend/src/demo/snapshot.json',
             'docs/competition-evidence/no-field-analysis.json', 'frontend/src/demo/no-field-analysis.json',
             'frontend/src/demo/snapshot-plan-review.json','frontend/src/demo/observed-snapshot-plan-review.json',
             'docs/competition-evidence/review-fix-results.json','frontend/src/demo/review-fix-summary.json',
             'docs/competition-evidence/tournament-scale-analysis.json',
             'backend/validation.py', 'tests/test_validation.py',
             'data/output/award-validation-pytest.xml', 'data/output/award-validation-node.xml',
             'data/output/award-validation-playwright.json']
    sources = {path: hashlib.sha256((ROOT/path).read_text(encoding='utf-8-sig').replace('\r\n', '\n').encode()).hexdigest() for path in paths}
    return {'generated_at': datetime.now(KST).isoformat(), 'scope': '고정 가상 대회 분석·소프트웨어 검증의 주장 대장',
            'hash_basis': 'UTF-8 텍스트, BOM 제거·LF 정규화. 수행 사실을 독립 인증하는 서명은 아님.',
            'source_sha256': sources, 'original_sample_sha256': sample.original_sha256,
            'tested_source_fingerprint': stamp['source_fingerprint'], 'test_run_started_at': stamp['started_at'],
            'assumptions': ASSUMPTIONS, 'observation_hours': len(sample.rows),
            'checks': {k: {'passed': v['passed'], 'count': len(v['checks'])} for k, v in checked.items()},
            'test_receipts': receipts, 'demo': replay['candidates'][0], 'method_comparison': comparison,'no_field_analysis':no_field,'tournament_scale':scale,'selection_fix':read('docs/competition-evidence/review-fix-results.json')['summary'],
            'incomplete_days': sum(r['assigned'] < 15 for r in replay['days']),
            'zero_assignment_dates': [r['date'] for r in replay['days'] if r['assigned'] == 0],
            'live': {k: live[k] for k in ('verified_at', 'status', 'upstream_http_status', 'diagnostic_timeout_seconds')},
            'unsupported_claims': ['수상권·수상 확률', '실제 운영자 업무 절감·구매 수요', '국내 구장 현장 정확도·사고 감소',
                                   '기본10초 최신 조회 안정성', '사람·경쟁 제품 대비 성능 우위'],
            'user_confirmation': '2026-10-06 사용자 확인: 실제 측정 자료 확보 불가. 실제 운영자·현장 측정 기록 없음. 오프라인 기술 검증과 조건 변화 검토를 제출 근거로 삼고 현장 정확도·효용은 미검증으로 둔다.'}


def markdown(data):
    comp = data['method_comparison']; demo = data['demo']; tests = data['test_receipts']
    cost = (comp['cp_common_heat']/comp['greedy_common_heat']-1)*100
    stronger=data['no_field_analysis']['baselines']['best_of_four']
    reduction=(1-stronger['cp_common_heat']/stronger['baseline_common_heat'])*100
    scale=data.get('tournament_scale')
    scale_note=(f"추가16팀·27경기·2일의31개 전 구간에서는 단순 기준{scale['baseline_assigned']}건 대비 엔진{scale['engine_assigned']}건으로 배정 합계가 더 적었다. 두 구간의 열세와18개 FEASIBLE·1개 폴백을 공개한다.12팀 결과를 대진 일반의 우위로 확대하지 않는다. [전체 결과와 한계](../tournament-scale-report.md)." if scale else '')
    return f'''# 심사자가 확인할 기술 증거 묶음

생성: {data['generated_at']}. 아래 기존 비교 표는 수정 전 고정 해의 역사적 분석이다. 현재 선택 수정 검증은 [수정 보고](../review-fix-report.md)와 [93조건 새 결과](review-fix-results.json)를 읽는다. 배점·수상 확률을 만들지 않는다. 공식 요강은 시제품과 서비스 링크·사진·활용 영상 등의 기술 자료를 허용한다. [공식 요강](https://ggsports.spectory.net/innovation/contest?bno=60730). 이 자료는 제출 주장을 원자료·전체 테스트에 연결하는 자체 검증이며 공식 심사 결과가 아니다.

| 확인 가능한 주장 | 수치와 조건 | 근거 |
|---|---|---|
| 관측 입력의 가상 대회 시연 | {demo['date']} {demo['assigned']}배정/{demo['postponed']}연기, 공통{demo['common_count']}경기 {demo['original_heat']}→{demo['proposed_heat']} | [62일 원본](../real-data/replay-results.json), 관측 스냅샷 |
| 더 엄격한 조합 탐색 비교 | 날짜별 유리한4종 단순 기준 {stronger['assigned']}→CP-SAT {comp['cp_assigned']}, 전부 배정 {stronger['complete_days']}→{comp['cp_complete_days']}일 | [전체62일·조건·검사](../no-field-analysis-report.md), [원자료](no-field-analysis.json) |
| 강한 기준과 공통 경기만의 비용 비교 | {stronger['baseline_common_heat']}→{stronger['cp_common_heat']}, {reduction:.2f}% 감소 | 현장 효과·사람·경쟁 제품 비교 아님 |
| 기존 약한 기준과의 비교도 보존 | 탐욕 {comp['greedy_assigned']}→CP-SAT {comp['cp_assigned']}, 배정 +{comp['assignment_gain']}건, 완전 배정 {comp['greedy_complete_days']}→{comp['cp_complete_days']}일 | [기존 동일 제약 비교](method-comparison.md) |
| 불리한 비용도 공개 | 공통 열 노출 {comp['greedy_common_heat']}→{comp['cp_common_heat']}, {cost:.2f}% 증가 | 같은 비교의 전체62일, 건강 효과 아님 |
| 일반화하지 않는 한계 | 동일일15경기 미완료 {data['incomplete_days']}일, 0배정 {len(data['zero_assignment_dates'])}일 | [조건부 분석](../wbgt-sanity-report.md) |
| 전체 검사의 기존 통과 유지 | Python {tests['python']['passed']}, Node {tests['node']['passed']}, 데스크톱·모바일 반복 {tests['browser']['passed']} 통과 | [주장 대장과 영수증 지문](verified-claims.json) |
| 실제 기상청 연결의 범위 | 실제 자료 수신 성공은 진단30초 모드, 기본10초는4회 시간 초과 | [실제 검증](../live-connection-report.md), 연결 안정성 확보 주장 불가 |
| 앞으로 실제 근거를 쌓는 기능 | 준비 포함 시간·부정 의견·측정 오차·제외 사유 기록 및 내보내기 | [기능 검사](../validation-feature-report.md), [오기입 처리](../validation-exclusion-report.md) |

가정: {data['assumptions']}. 날짜별 같은15경기의 반복 배정 건수이며 실제 살린 경기 수가 아니다. 각 비교의 공통 경기 집합이 다르므로 다른 행의 점수를 합쳐 주장하지 않는다. 관측 시연의 추정 중앙 최고32.043℃와 범위30.543~33.543℃는 현장 WBGT 실측이 아니다.

{data['user_confirmation']}

{scale_note}

고정 일정의 조건 변화 검토도 공개한다. 원래 추정59일은 모두 제약 통과, +1℃41일·+2℃57일은 권고·제약 재검토 대상, 배정 구장·시간1개 누락은59일 전부 재검토 대상이었다. 배정0인3일은 제외한다. 재최적화 후 개최 불가 일수가 아니고 실제 오차·확률도 아니다. −1℃에도 단축 해제 등으로 종료 시각이 늘어날 수 있다. 제안/승인 입력을 바꾸지 않는 [검토 기능](../plan-review-report.md)으로 같은 조건을 재확인한다.

## 3분 시연으로 확인하는 순서

1. 관측 스냅샷 재현: 관측 입력·가상 대회·사전 계산 라벨을 먼저 보여준다.
2. 히트맵 → 상세 입력 근거: 추정·범위, 일사 결측 처리와 구장 보정 가정을 확인한다.
3. 재편성 비교 → 경기 근거: 배정/연기와 선행·휴식·일몰 제약, 원래→제안 내역을 확인한다.
4. 승인 → 모의 안내 → PDF: 운영자 결정과 근거가 남는 전체 흐름을 확인한다.
5. 질의응답 부록으로62일 전체 결과·불리한 비용을 보여준다. 본 발표420초 구성은 바꾸지 않는다.

새 **검증 기록**은 일반 실행의 별도 검증 도구다. 빈 실제 집계도 숨기지 않는다. 인터뷰를 수행한 듯 시연하거나 모의 기록을 현장 실적으로 제출하지 않는다. 실제 참여 동의·원자료를 확보한 뒤 자료 구분을 바꾸어 입력한다. 비교·측정의 선언은 입력자 확인이며 독립 검증이 아니다.

## 재검증

루트의 프로젝트 가상환경으로 전체 pytest를 실행하여 `data/output/award-validation-pytest.xml`을 만들고, 프론트엔드의 Node JUnit과 Playwright JSON 영수증을 만든 뒤 `scripts/build_award_evidence.py`를 실행한다. 정확한 명령은 [README](../../README.md)에 있다. 실패·중단·재시도 실패·검사 수 감소·관측 지문 불일치·기존 정합성 실패가 있으면 갱신을 거부한다. 데이터 해시는 원본 일치 확인 수단이며 수행이나 수상 가능성을 독립 인증하지 않는다.

[제출 주장 목록](../submission/evidence.md) · [실제 검증 계획](../submission/validation-plan.md) · [종합 보고](../award-evidence-report.md)
'''


if __name__ == '__main__' and sys.argv[1:] == ['--stamp']:
    path = ROOT/'data/output/award-validation-source.json'; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'source_fingerprint': source_fingerprint(), 'started_at': datetime.now(KST).isoformat()}, indent=2)+'\n', encoding='utf-8')
    print('Test source fingerprint recorded. No network or credential loading.')
    raise SystemExit(0)
if __name__ == '__main__':
    data = collect()
    folder = ROOT/'docs/competition-evidence'
    (folder/'verified-claims.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (folder/'proof-pack.md').write_text(markdown(data), encoding='utf-8')
    print(json.dumps({'passed': True, 'checks': data['checks'], 'test_receipts': data['test_receipts']}, ensure_ascii=True))
