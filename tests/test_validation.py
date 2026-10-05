import copy
import csv
import io
import json
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.validation import fingerprint


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path/'validation.sqlite3')
    risk = {'venue_id': 'field', 'valid_time': '2026-07-10T12:00:00+09:00', 'is_mock': False,
            'wbgt_c': 32.5, 'wbgt_low_c': 31, 'wbgt_high_c': 34, 'inputs_hash': 'original-input-hash',
            'inputs': {'venue': {'id': 'field', 'name': '검증용 실제 구장', 'is_mock': False,
                                 'field_offset_c': 2.5, 'surface': 'natural_grass'},
                       'settings': {'surface_offsets': {'natural_grass': 0}}, 'calibration': None,
                       'weather': {'source': 'asos_obs', 'station_id': 119}}}
    app.state.repo.put('sessions', 'reference', {'id': 'reference', 'label': '테스트용 관측 입력', 'risks': [risk]})
    with TestClient(app) as c: yield c


def work(**kwargs):
    timing = {'preparation_min': 5, 'change_min': 10, 'documentation_min': 5, 'completed': True, 'constraint_check': 'passed'}
    return {'mode': 'actual', 'source_ref': 'source1', 'observed_at': '2026-07-10T12:00:00+09:00',
            'participant_code': 'P1', 'case_code': 'C1', 'consent': True, 'order': 'current_first',
            'same_conditions': True, 'current': timing, 'heattime': {**timing, 'preparation_min': 10},
            'negative_feedback': 'CSV 준비가 더 오래 걸림', 'purchase_response': '도입 거절', **kwargs}


def field(**kwargs):
    return {'mode': 'actual', 'source_ref': 'meter1', 'observed_at': '2026-07-10T12:00:00+09:00',
            'session_id': 'reference', 'venue_id': 'field', 'reference_time': '2026-07-10T12:00:00+09:00',
            'measured_wbgt_c': 30, 'device_code': 'D1', 'protocol_ref': 'protocol1',
            'measurement_height_m': 1.2, 'placement': '테스트에서 선언한 동일 위치',
            'calibration_status': 'documented', 'same_site': True, **kwargs}


def summary(client): return client.get('/api/validation/summary').json()


def test_empty_is_unperformed(client):
    s = summary(client)
    assert s['work']['included_pairs'] == s['work']['participants'] == s['field']['included_pairs'] == 0
    assert s['work']['median_saved_min'] is None
    assert s['field']['mae_c'] is s['field']['bias_c'] is s['field']['range_inclusion_fraction'] is None


def test_preparation_and_unfavourable_result_preserved(client):
    assert client.post('/api/validation/work', json=work()).status_code == 201
    s = summary(client)
    assert s['work']['median_saved_min'] == -5
    assert s['work_records'][0]['heattime_total_min'] == 25
    assert s['work_records'][0]['negative_feedback'] == 'CSV 준비가 더 오래 걸림'
    assert s['work_records'][0]['purchase_response'] == '도입 거절'


@pytest.mark.parametrize('changes,reason', [
    ({'mode': 'mock'}, '가상 예시'), ({'same_conditions': False}, '동일'),
    ({'current': {**work()['current'], 'completed': False}}, '중단'),
    ({'heattime': {**work()['heattime'], 'preparation_min': None}}, '누락'),
    ({'current': {**work()['current'], 'constraint_check': 'failed'}}, '하드 제약'),
    ({'heattime': {**work()['heattime'], 'constraint_check': 'unchecked'}}, '하드 제약'),
])
def test_ineligible_work_kept_but_not_counted(client, changes, reason):
    r = client.post('/api/validation/work', json=work(**changes)); assert r.status_code == 201
    assert any(reason in x for x in r.json()['excluded_reasons'])
    s = summary(client); assert s['work']['records'] == 1
    assert s['work']['included_pairs'] == 0 and s['work']['median_saved_min'] is None


@pytest.mark.parametrize('changes', [
    {'consent': False}, {'participant_code': '실명 금지'}, {'source_ref': 'https://secret?key=x'},
    {'observed_at': '2026-07-10T12:00:00'}, {'observed_at': (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()},
    {'current': {**work()['current'], 'preparation_min': -1}}, {'unexpected': 'ignored?'}
])
def test_invalid_work_rejected_without_write(client, changes):
    assert client.post('/api/validation/work', json=work(**changes)).status_code == 422
    assert summary(client)['work']['records'] == 0


def test_work_orders_cases_and_distinct_people(client):
    rows = [work(), work(order='heattime_first'), work(participant_code='P2', case_code='C2')]
    for r in rows: assert client.post('/api/validation/work', json=r).status_code == 201
    assert client.post('/api/validation/work', json=rows[0]).status_code == 409
    s = summary(client)
    assert s['work']['included_pairs'] == 3 and s['work']['participants'] == 2
    assert s['work']['order_counts'] == {'current_first': 2, 'heattime_first': 1}
    assert s['work_cases']['C1']['included_pairs'] == 2
    assert s['work_cases']['C2']['participants'] == 1


def test_field_known_arithmetic_and_frozen_input(client):
    before = copy.deepcopy(client.app.state.repo.get('sessions', 'reference'))
    r = client.post('/api/validation/field', json=field()); assert r.status_code == 201
    saved = r.json()
    assert saved['model_base_c'] == 30 and saved['error_c'] == 2.5 and saved['base_error_c'] == 0
    assert saved['inside_range'] is False
    assert saved['reference_fingerprint'] == fingerprint(before['risks'][0])
    assert client.app.state.repo.get('sessions', 'reference') == before
    before['risks'][0]['wbgt_c'] = 99
    client.app.state.repo.put('sessions', 'reference', before)
    s = summary(client)
    assert s['field_records'][0]['frozen_risk']['wbgt_c'] == 32.5
    assert s['field']['mae_c'] == s['field']['bias_c'] == 2.5
    assert s['field']['base_mae_c'] == s['field']['base_bias_c'] == 0
    assert s['field']['range_inclusion_fraction'] == 0


@pytest.mark.parametrize('changes,mutate,reason', [
    ({'mode': 'mock'}, None, '가상 예시'), ({}, 'mock_weather', '합성'), ({}, 'mock_venue', '가상 구장'),
    ({'observed_at': '2026-07-10T12:01:00+09:00'}, None, '시각 불일치'),
    ({'same_site': False}, None, '위치'), ({'calibration_status': 'unknown'}, None, '교정'),
    ({}, 'calibration', '순환'),
])
def test_excluded_field_reasons(client, changes, mutate, reason):
    if mutate:
        session = client.app.state.repo.get('sessions', 'reference'); r = session['risks'][0]
        if mutate == 'mock_weather': r['is_mock'] = True
        if mutate == 'mock_venue': r['inputs']['venue']['is_mock'] = True
        if mutate == 'calibration': r['inputs']['calibration'] = {'offset_c': 1}
        client.app.state.repo.put('sessions', 'reference', session)
    r = client.post('/api/validation/field', json=field(**changes)); assert r.status_code == 201
    assert any(reason in x for x in r.json()['excluded_reasons'])
    s = summary(client)
    assert s['field']['included_pairs'] == 0 and s['field']['mae_c'] is None
    assert s['field']['records'] == 1


@pytest.mark.parametrize('changes,status', [
    ({'session_id': 'missing'}, 404), ({'venue_id': 'missing'}, 404),
    ({'reference_time': '2026-07-10T13:00:00+09:00'}, 404),
    ({'measured_wbgt_c': 66}, 422), ({'measurement_height_m': 0}, 422),
    ({'reference_time': '2026-07-10T12:00:00'}, 422), ({'device_code': '=1'}, 422)
])
def test_invalid_field_not_written(client, changes, status):
    assert client.post('/api/validation/field', json=field(**changes)).status_code == status
    assert summary(client)['field']['records'] == 0


def test_field_duplicate_across_session_timezone_alias(client):
    assert client.post('/api/validation/field', json=field()).status_code == 201
    client.app.state.repo.put('sessions', 'another', client.app.state.repo.get('sessions', 'reference'))
    assert client.post('/api/validation/field', json=field(session_id='another', reference_time='2026-07-10T03:00:00+00:00')).status_code == 409


def test_negative_bias_and_range_edges(client):
    assert client.post('/api/validation/field', json=field(measured_wbgt_c=34)).status_code == 201
    s = summary(client)['field']
    assert s['mae_c'] == 1.5 and s['bias_c'] == -1.5 and s['range_inclusion_fraction'] == 1


def test_zero_work_duration_not_missing(client):
    timing = {k: 0 if k.endswith('_min') else v for k, v in work()['current'].items()}
    assert client.post('/api/validation/work', json=work(current=timing, heattime=timing)).status_code == 201
    assert summary(client)['work']['median_saved_min'] == 0


def test_export_all_rows_unicode_fingerprints_and_no_mutation_route(client):
    client.post('/api/validation/work', json=work(mode='mock', notes='=HYPERLINK("x") · 의견'))
    client.post('/api/validation/field', json=field())
    data = client.get('/api/validation/export/json').json()
    assert len(data['work_records']) == len(data['field_records']) == 1
    rows = list(csv.DictReader(io.StringIO(client.get('/api/validation/export/csv').content.decode('utf-8-sig'))))
    assert len(rows) == 2
    for r in rows:
        body = json.loads(r['record_json'])
        assert r['record_fingerprint'] == fingerprint({k: v for k, v in body.items() if k != 'record_fingerprint'})
    assert '=HYPERLINK' in rows[0]['record_json']
    assert client.get('/api/validation/export/pdf').status_code == 404
    assert client.put('/api/validation/work', json=work()).status_code == 405


def test_does_not_load_key_or_apply_manual_calibration(client, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('key or manual measurement must not be used')
    monkeypatch.setattr('backend.weather.aws_live.load_key', forbidden)
    monkeypatch.setattr(client.app.state.service.weather, 'save_manual', forbidden)
    assert client.post('/api/validation/field', json=field()).status_code == 201
    assert client.post('/api/validation/work', json=work()).status_code == 201


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity'])
def test_nonfinite_raw_json_rejected(client, value):
    raw = json.dumps(field()).replace('"measured_wbgt_c": 30', '"measured_wbgt_c": '+value)
    assert client.post('/api/validation/field', content=raw, headers={'Content-Type': 'application/json'}).status_code == 422


@pytest.mark.parametrize('kind,factory', [('work', work), ('field', field)])
def test_exclusion_audited_without_changing_original(client, kind, factory):
    original = client.post('/api/validation/'+kind, json=factory()).json()
    assert summary(client)[kind]['included_pairs'] == 1
    url = '/api/validation/'+kind+'/'+original['id']+'/exclude'
    assert client.post(url, json={'reason': '원자료 시각 오기입 확인'}).status_code == 201
    s = summary(client)
    assert s[kind]['included_pairs'] == 0 and s[kind]['excluded_actual'] == 1
    assert s[kind+'_records'][0] == original
    assert s['exclusions'][0]['reason'] == '원자료 시각 오기입 확인'
    assert client.post(url, json={'reason': '유리한 수치로 덮어쓰기'}).status_code == 409
    rows = list(csv.DictReader(io.StringIO(client.get('/api/validation/export/csv').content.decode('utf-8-sig'))))
    assert rows[0]['eligible'] == 'False'
    assert json.loads(rows[0]['record_json']) == original
    assert json.loads(rows[0]['review_exclusion_json'])['record_id'] == original['id']


@pytest.mark.parametrize('path,reason,status', [('work/missing', '오기입', 404), ('unknown/missing', '오기입', 404), ('work/missing', '  ', 422)])
def test_invalid_exclusion_does_not_create_audit(client, path, reason, status):
    assert client.post('/api/validation/'+path+'/exclude', json={'reason': reason}).status_code == status
    assert summary(client)['exclusions'] == []


def test_live_reference_requires_explicit_save_without_extra_weather_call(client, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('credentials or network forbidden')
    provider=client.app.state.live_provider
    provider.key_loader=forbidden;provider.transport=forbidden
    response=client.post('/api/live-observations', json={'mode':'mock'}).json()
    assert response['status']=='mock' and len(response['reference_token'])==64
    assert client.get('/api/validation/references').json()==[]
    before=client.app.state.repo.list('sessions')
    saved=client.post('/api/validation/live-reference', json={'token':response['reference_token']})
    assert saved.status_code==201
    ref=saved.json();assert ref['risks']==response['risks']
    assert client.app.state.repo.list('sessions')==before
    assert client.get('/api/validation/references').json()==[ref]
    risk=ref['risks'][0]
    record=client.post('/api/validation/field',json=field(mode='mock',session_id=ref['id'],venue_id=risk['venue_id'],reference_time=risk['valid_time']))
    assert record.status_code==201
    assert '합성 기상 입력' in record.json()['excluded_reasons']
    assert record.json()['frozen_risk']==risk


@pytest.mark.parametrize('token,status', [('a'*64,409), ('x',422)])
def test_invalid_or_stale_live_reference_cannot_inject_risk(client, token, status):
    assert client.post('/api/validation/live-reference',json={'token':token}).status_code==status
    assert client.get('/api/validation/references').json()==[]


def test_cached_reference_cannot_be_overwritten_by_new_live_calc(client):
    result=client.post('/api/live-observations',json={'mode':'mock'}).json()
    old=client.post('/api/validation/live-reference',json={'token':result['reference_token']}).json()
    newer=client.post('/api/live-observations',json={'mode':'mock','engine_settings':{'uncertainty_c':2}}).json()
    assert newer['reference_token']!=result['reference_token']
    assert client.post('/api/validation/live-reference',json={'token':result['reference_token']}).status_code==409
    assert client.get('/api/validation/references').json()==[old]


def test_injected_observed_live_reference_supports_actual_site_comparison(client):
    from pathlib import Path
    from backend.weather.aws_live import LiveProvider
    from backend.weather.models import KST
    calls=[]
    def transport(*args):
        calls.append(1)
        return (Path(__file__).parent/'fixtures/aws-119-20261005-2335.txt').read_bytes()
    venue=client.app.state.repo.list('venues')[0]
    client.app.state.repo.put('venues','real-field-test',{**venue,'id':'real-field-test','name':'시험용 실제 구장 선언','is_mock':False})
    client.app.state.live_provider=LiveProvider(client.app.state.repo,key_loader=lambda:'fake-key',transport=transport,
                                               clock=lambda:datetime(2026,10,5,23,38,tzinfo=KST))
    live=client.post('/api/live-observations',json={'mode':'api'}).json()
    assert live['status']=='ready'
    ref=client.post('/api/validation/live-reference',json={'token':live['reference_token']}).json()
    risk=next(r for r in ref['risks'] if r['venue_id']=='real-field-test')
    record=client.post('/api/validation/field',json=field(session_id=ref['id'],venue_id=risk['venue_id'],
                                                       reference_time=risk['valid_time'],observed_at=risk['valid_time']))
    assert record.status_code==201 and record.json()['eligible']
    assert record.json()['frozen_risk']==risk
    assert len(calls)==1
    assert summary(client)['field']['included_pairs']==1
    assert summary(client)['field']['bias_c']==pytest.approx(risk['wbgt_c']-30)
