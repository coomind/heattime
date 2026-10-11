from io import BytesIO, StringIO
import csv
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from backend.app import create_app
from backend.exports import records_pdf, records_csv, csv_safe
from backend.notifications import build_notifications, RealSender
from backend.schedule.models import Match
from backend.schedule.optimizer import participants


@pytest.fixture(scope='module')
def approved(tmp_path_factory):
    c = TestClient(create_app(tmp_path_factory.mktemp('p5') / 'db.sqlite3'))
    sid = c.post('/api/replays', json={'date': '2026-08-01'}).json()['id']
    assert c.post(f'/api/sessions/{sid}/optimize').status_code == 200
    r = c.post(f'/api/sessions/{sid}/decision', json={'action': 'accepted', 'reason': '가상 예시 검토 사유'})
    assert r.status_code == 200
    return r.json()


def test_mock_notifications_per_team_and_postponement(approved, monkeypatch):
    import socket
    def blocked(*args, **kwargs): raise AssertionError('mock attempted network')
    monkeypatch.setattr(socket, 'create_connection', blocked)
    logs = build_notifications(approved)
    possible = participants([Match(**m) for m in approved['matches']])
    for m in approved['matches']:
        rows = [n for n in logs if n['match_id'] == m['id']]
        assert {n['team_id'] for n in rows} == possible[m['id']]
        assert all(n['channel'] == 'mock' and '가상 예시' in n['recipient'] for n in rows)
        assert all('쿨링브레이크' in n['message'] and '수분 보충' in n['message'] for n in rows)
    for p in approved['decision']['postponed']:
        rows = [n for n in logs if n['match_id'] == p['match_id']]
        assert rows and all(p['reason'] in n['message'] and '연기' in n['message'] for n in rows)
    with pytest.raises(NotImplementedError): RealSender().send({}, 'x', '')


def test_pdf_full_evidence_font_and_each_page_notice(approved):
    reader = PdfReader(BytesIO(records_pdf(approved)))
    text = '\n'.join(p.extract_text() for p in reader.pages)
    for field in ['수집 시각', '입력 기온', '습도', '풍속', '사용 일사', '일사량 추정', '범위',
                  '원래 일정', '승인 일정', '산정 방법', '입력 해시', '정책', '출처', '판단 사유',
                  '현장 보정', '가상 예시 검토 사유', 'WBGT 설정', '연기']:
        assert field in text
    assert all('본 자료는 의사결정 보조용 추정값' in p.extract_text() for p in reader.pages)
    embedded = []
    for p in reader.pages:
        for ref in p['/Resources']['/Font'].values():
            descriptor = ref.get_object().get('/FontDescriptor')
            if descriptor: embedded.append('/FontFile2' in descriptor.get_object())
    assert any(embedded), 'Korean font must be embedded'


def test_csv_applied_schedule_and_traceability(approved):
    rows = list(csv.DictReader(StringIO(records_csv(approved).decode('utf-8-sig'))))
    assert {r['match_id'] for r in rows} == {m['id'] for m in approved['matches']}
    assignments = {a['match_id']: a for a in approved['decision']['assignments']}
    for r in rows:
        assert r['inputs_hash'] and r['fetched_at'] and r['policy_source']
        # E-3: range columns say what they bound.
        assert float(r['WBGT 추정 하한']) <= float(r['WBGT 추정']) <= float(r['WBGT 추정 상한'])
        assert r['reason'] == approved['decision']['reason']
        if r['match_id'] in assignments:
            assert r['applied_start'] == assignments[r['match_id']]['start']
    for p in approved['decision']['postponed']:
        assert any(r['postponement_reason'] == p['reason'] for r in rows if r['match_id'] == p['match_id'])
    assert csv_safe('=1+1').startswith("'")
    assert csv_safe(' @attack').startswith("'")
    # B-8: real negative numbers stay numeric; text that merely starts with '-' is still neutralized.
    assert csv_safe(-1.5)=='-1.5' and csv_safe(-2)=='-2' and csv_safe(0.0)=='0.0'
    assert csv_safe('-1+cmd').startswith("'") and csv_safe('-3').startswith("'")


def test_decision_snapshot_survives_later_session_edit(approved):
    from copy import deepcopy
    changed = deepcopy(approved)
    changed['weather'] = []; changed['risks'] = []; changed['recommendations'] = []
    assert records_csv(changed) == records_csv(approved)
    assert '가상 예시 검토 사유' in ''.join(p.extract_text() for p in PdfReader(BytesIO(records_pdf(changed))).pages)


def test_deployment_config_mock_and_secret_exclusion():
    import yaml
    root = Path(__file__).parents[1]
    service = yaml.safe_load((root/'render.yaml').read_text(encoding='utf-8'))['services'][0]
    assert service['runtime'] == 'docker' and service['plan'] == 'free'
    assert service['healthCheckPath'] == '/api/health'
    docker = (root/'Dockerfile').read_text(encoding='utf-8')
    assert 'npm ci' in docker and 'npm run build' in docker and 'backend.run' in docker
    assert 'COPY data/mock/' in docker
    ignore = (root/'.dockerignore').read_text(encoding='utf-8')
    assert '.env' in ignore and '.env.*' in ignore and 'data/**' in ignore
