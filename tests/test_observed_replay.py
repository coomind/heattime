from datetime import date
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.engine.settings import EngineSettings
from backend.schedule.models import ScheduleSettings
from backend.weather.asos_samples import ROOT,load_dataset
from scripts.replay_asos_dates import candidate_order


def test_observed_replay_metadata_and_default_settings(tmp_path):
    client=TestClient(create_app(tmp_path/'api.sqlite3'))
    info=client.get('/api/observations').json()
    assert len(info['dates'])==62 and info['station']['id']=='119'
    response=client.post('/api/replays',json={'date':'2026-07-01','mode':'observed'})
    assert response.status_code==200
    session=response.json()
    assert '기상청 관측 자료(수원 119·2026-07-01)' in session['label']
    assert session['data_origin']=='kma_observed' and session['mode']=='observed'
    assert len(session['weather'])==72 and len(session['risks'])==72 and len(session['matches'])==15
    assert all(not p['is_mock'] and p['station_id']=='119' for p in session['weather'])
    assert all(not r['is_mock'] and not r['inputs']['weather']['is_mock'] for r in session['risks'])
    assert all(v['is_mock'] for v in session['venues']) and all(t['is_mock'] for t in session['teams'])
    assert session['engine_settings']==EngineSettings().model_dump()
    assert session['schedule_settings']==ScheduleSettings().model_dump()
    assert client.post('/api/replays',json={'date':'2026-09-01','mode':'observed'}).status_code==422
    assert client.post('/api/replays',json={'mode':'live'}).status_code==422
    mock=client.post('/api/replays',json={'date':'2026-07-01'}).json()
    assert mock['data_origin']=='synthetic' and all(p['is_mock'] for p in mock['weather'])


def test_candidate_order_prioritizes_postponements_then_salvaged_matches():
    rows=[{'postponed':1,'salvaged':15,'heat_reduction':9999,'date':'2026-07-01'},
          {'postponed':0,'salvaged':10,'heat_reduction':1,'date':'2026-07-02'},
          {'postponed':0,'salvaged':9,'heat_reduction':9999,'date':'2026-07-03'}]
    assert sorted(rows,key=candidate_order)[0]['date']=='2026-07-02'
