from pathlib import Path
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from backend.app import create_app

@pytest.fixture
def client(tmp_path):return TestClient(create_app(tmp_path/'app.sqlite3'))

def replay(c):
    r=c.post('/api/replays',json={'date':'2026-08-01'})
    assert r.status_code==200,r.text
    return r.json()

def test_full_replay_approval_logs_pdf_csv_and_persistence(client):
    s=replay(client);sid=s['id']
    assert len(s['risks'])==72 and len(s['teams'])==12 and len(s['matches'])==15
    assert all(r['wbgt_low_c']<=r['wbgt_c']<=r['wbgt_high_c'] for r in s['risks'])
    assert '가상 예시' in s['label']
    detail=client.get(f'/api/sessions/{sid}/matches/g1-1')
    assert detail.status_code==200 and len(detail.json()['risks'])==24
    p=client.post(f'/api/sessions/{sid}/optimize').json()
    assert p['constraints_ok'] and p['assignments']
    r=client.post(f'/api/sessions/{sid}/decision',json={'action':'accepted','reason':'가상 예시 운영 검토'})
    assert r.status_code==200,r.text
    assert r.json()['decision']['snapshot']['weather']
    notifications=client.get(f'/api/sessions/{sid}/notifications').json();assert notifications
    pdf=client.get(f'/api/sessions/{sid}/export/pdf');assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
    reader=PdfReader(BytesIO(pdf.content));text=''.join(p.extract_text() for p in reader.pages)
    assert 'WBGT' in text and '가상 예시' in text and '의사결정 보조용 추정값' in text
    csv=client.get(f'/api/sessions/{sid}/export/csv').content.decode('utf-8-sig')
    assert '가상 예시' in csv and 'WBGT 추정' in csv
    duplicate=client.post(f'/api/sessions/{sid}/decision',json={'action':'accepted','reason':'duplicate'})
    assert duplicate.status_code==422
    assert client.get(f'/api/sessions/{sid}/notifications').json()==notifications
    restarted=TestClient(create_app(client.app.state.repo.path))
    assert restarted.get(f'/api/sessions/{sid}').json()['decision']==r.json()['decision']

def test_reject_does_not_issue_mock_notifications(client):
    s=replay(client);sid=s['id'];client.post(f'/api/sessions/{sid}/optimize')
    r=client.post(f'/api/sessions/{sid}/decision',json={'action':'rejected','reason':'재검토 필요'})
    assert r.status_code==200 and not r.json()['notifications']

def test_unsafe_modified_plan_rejected(client):
    sid=replay(client)['id'];p=client.post(f'/api/sessions/{sid}/optimize').json()
    assignments=[{'match_id':a['match_id'],'venue_id':a['venue_id'],'start':a['start']} for a in p['assignments']]
    assignments[0]['start']='2026-08-01T03:00:00+09:00'
    r=client.post(f'/api/sessions/{sid}/decision',json={'action':'modified','reason':'수정','assignments':assignments})
    assert r.status_code==422
    assert client.get(f'/api/sessions/{sid}').json()['decision'] is None

def test_crud_csv_relations_and_atomic_invalid_import(client):
    v={'id':'test-venue','name':'가상 예시','lat':37.2,'lon':127.0}
    assert client.post('/api/venues',json=v).status_code==201
    assert client.post('/api/venues',json=v).status_code==409
    v['name']='가상 예시 수정';assert client.put('/api/venues/test-venue',json=v).status_code==200
    assert client.delete('/api/venues/test-venue').status_code==204
    assert client.delete('/api/venues/mock-suwon-a').status_code==409
    header='id,round,team_a,team_b,venue_id,scheduled_start,duration_min,depends_on\n'
    valid='csv-1,조별,t1,t2,mock-suwon-a,2026-08-01T09:00:00+09:00,40,\n'
    bad='csv-2,조별,t1,t2,unknown,2026-08-01T10:00:00+09:00,40,\n'
    before=client.get('/api/matches').json()
    assert client.post('/api/tournaments/demo/matches/csv',json={'csv_text':header+valid+bad}).status_code==404
    assert client.get('/api/matches').json()==before
    assert client.post('/api/tournaments/demo/matches/csv',json={'csv_text':header+valid}).json()['imported']==1
    assert client.delete('/api/matches/csv-1').status_code==204

def test_manual_invalid_time_and_live_mode_rejected(client):
    r=client.post('/api/manual',json={'venue_id':'mock-suwon-a','valid_time':'2026-08-01T12:00:00','wbgt_c':31})
    assert r.status_code==422
    assert client.post('/api/replays',json={'date':'2026-08-01','mode':'live'}).status_code==422
    assert client.get('/api/sessions/unknown').status_code==404
