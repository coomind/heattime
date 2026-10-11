import base64
from copy import deepcopy
from datetime import date,datetime
from io import BytesIO
import hashlib
import json
from pypdf import PdfReader
import pytest
from backend.repository import Repository
from backend.service import Service
from backend.exports import records_pdf,records_csv,DISCLAIMER
from backend.engine.settings import EngineSettings
from backend.schedule.models import ScheduleSettings
from backend.schedule.optimizer import Candidate,validate
from backend.weather.asos_samples import ROOT,load_dataset
from backend.demo_config import demo_date


@pytest.fixture(scope='module')
def approved(tmp_path_factory):
    service=Service(Repository(tmp_path_factory.mktemp('real-records')/'db.sqlite3'))
    s=service.replay(date(2026,8,10),mode='observed')
    service.optimize(s['id'])
    return service.decide(s['id'],'accepted','가상 예시 운영자','실제 관측 입력의 가상 대회 시연')


def test_live_observed_pdf_source_and_frozen_labels(approved):
    reader=PdfReader(BytesIO(records_pdf(approved)))
    pages=[p.extract_text() for p in reader.pages];text='\n'.join(pages)
    assert '기상청 관측 자료(수원 119·2026-08-10)' in pages[0]
    assert all(DISCLAIMER in p for p in pages)
    assert '비교 일사량은 합성' not in text and '시간평균' in text
    assert load_dataset().original_sha256 in text and '기상청 관측 자료' in pages[1]
    assert '관측 일사 결측 9시간' in text
    mutated=deepcopy(approved);mutated['label']='wrong';mutated['data_origin']='synthetic';mutated['weather']=[]
    frozen=''.join(p.extract_text() for p in PdfReader(BytesIO(records_pdf(mutated))).pages)
    assert '기상청 관측 자료(수원 119·2026-08-10)' in frozen and '비교 일사량은 합성' not in frozen
    assert '기상청 관측 자료(수원 119·2026-08-10)' in records_csv(approved).decode('utf-8-sig')


def test_missing_hour_is_explicit_in_pdf_evidence(approved):
    from fastapi.encoders import jsonable_encoder
    from backend.schedule.recommend import recommend
    s=deepcopy(approved);s['decision']=None
    t,m,v,r,settings,engine=Service.context(s)
    match=m[0].model_copy(update={'scheduled_start':m[0].scheduled_start.replace(hour=0,minute=0)})
    s['matches'][0]=jsonable_encoder(match)
    s['recommendations'][0]=jsonable_encoder(recommend(match,r,engine))
    text=''.join(p.extract_text() for p in PdfReader(BytesIO(records_pdf(s))).pages)
    assert '일사 관측 에너지 결측 · 모델 추정 사용' in text
    assert 'NoneMJ' not in text and 'None~None' not in text


def test_real_snapshot_matches_ranked_replay_and_preserves_defaults():
    bundle=json.loads((ROOT/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'));s=bundle['approved']
    results=json.loads((ROOT/'docs/real-data/replay-results.json').read_text(encoding='utf-8'))
    # Author decision 2026-10-11: the demo date is the first hot candidate (daily max air temp >= 31C, then the
    # unchanged rule): [2026-08-10, 2026-08-14, 2026-07-14, 2026-08-09, 2026-08-11]. The all-day rule order is kept.
    assert [c['date'] for c in results['candidates']]==['2026-07-03','2026-08-20','2026-07-10']
    assert [c['date'] for c in results['hot_candidates']]==['2026-08-10','2026-08-14','2026-07-14','2026-08-09','2026-08-11']
    best=results['hot_candidates'][0]
    assert best['date']==demo_date()=='2026-08-10' and best['max_ta_c']==31.6
    assert s['mode']=='snapshot-observed' and s['data_origin']=='kma_observed'
    assert s['tournament']['date_start']==best['date'] and s['id']==best['session_id']
    assert '관측 시연 스냅샷' in s['label'] and '기상청 관측 자료(수원 119·2026-08-10)' in s['label']
    assert all(not p['is_mock'] for p in s['weather']) and all(not r['is_mock'] for r in s['risks'])
    assert s['engine_settings']==EngineSettings().model_dump() and s['schedule_settings']==ScheduleSettings().model_dump()
    assert s['proposal']['original_heat_score']==best['original_heat'] and s['proposal']['proposed_heat_score']==best['proposed_heat']
    assert s['decision']['assignments']==s['proposal']['assignments']
    # 8/10: 13 assigned, semi2 postponed by constraints and final because its predecessor is postponed.
    assert len(s['decision']['assignments'])==13 and [p['match_id'] for p in s['decision']['postponed']]==['final','semi2']
    assert s['decision']['postponed']==s['proposal']['postponed'] and s['proposal']['postponed_count']==2
    assert s['proposal']['postponed'][0]['reason']=='선행 경기 연기' and s['proposal']['cp_sat_status']=='OPTIMAL'
    assert sum(r['level']==4 for r in s['recommendations'])==14 and sum(r['level']==3 for r in s['recommendations'])==1
    t,m,v,r,settings,engine=Service.context(s)
    assigned=[Candidate(**{**a,'start':datetime.fromisoformat(a['start']),'end':datetime.fromisoformat(a['end'])}) for a in s['decision']['assignments']]
    assert validate(assigned,m,t,v,r,settings)==[]
    assert all(n['channel']=='mock' and '가상 예시' in n['recipient'] for n in s['notifications'])
    fingerprint=hashlib.sha256(json.dumps({k:s[k] for k in ['weather','engine_settings','schedule_settings','policy']},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    assert fingerprint==bundle['input_fingerprint']


def test_observed_snapshot_exports_and_synthetic_bundle_remain_distinct():
    bundle=json.loads((ROOT/'frontend/src/demo/observed-snapshot.json').read_text(encoding='utf-8'))
    exports=json.loads((ROOT/'frontend/src/demo/observed-snapshot-exports.json').read_text(encoding='utf-8'))
    old=json.loads((ROOT/'frontend/src/demo/snapshot.json').read_text(encoding='utf-8'))
    assert exports['input_fingerprint']==bundle['input_fingerprint']!=old['input_fingerprint']
    assert all(p['is_mock'] for p in old['approved']['weather'])
    reader=PdfReader(BytesIO(base64.b64decode(exports['pdf_base64'])))
    text='\n'.join(p.extract_text() for p in reader.pages)
    assert all(DISCLAIMER in p.extract_text() for p in reader.pages)
    assert '기상청 관측 자료(수원 119·2026-08-10)' in text and '관측 시연 스냅샷' in text
    assert '실제 운영 판단 기록 아님' in text and '비교 일사량은 합성' not in text
    assert '기상청 관측 자료(수원 119·2026-08-10)' in exports['csv_utf8']


def test_packaged_observations_include_only_sanitized_files():
    docker=(ROOT/'Dockerfile').read_text(encoding='utf-8')
    ignore=(ROOT/'.dockerignore').read_text(encoding='utf-8')
    for required in ('data/observations/', 'docs/kma/asos-stations.json', 'docs/real-data/replay-results.json'):
        assert 'COPY '+required in docker
    assert '!data/observations/**' in ignore and 'data/**' in ignore
    assert '.env' in ignore and '.env.*' in ignore
    assert 'COPY data/samples/' not in docker
